import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"


def load_scheduler(tmp_path, monkeypatch):
    env_file = tmp_path / "emby_keepalive.env"
    env_file.write_text(
        "\n".join(
            [
                "EMBY_URL='https://example.test'",
                "EMBY_USERNAME='user'",
                "EMBY_PASSWORD='***'",
                "EMBY_MIN_DAYS='22'",
                "EMBY_MAX_DAYS='28'",
                "EMBY_MIN_PLAY_SECONDS='301'",
                "EMBY_SOFT_MAX_PLAY_SECONDS='600'",
                "EMBY_HARD_MAX_PLAY_SECONDS='1199'",
                "EMBY_PREFER_SOFT_MAX_PROB='0.85'",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    unit_dir = tmp_path / "systemd"
    unit_dir.mkdir()
    monkeypatch.setenv("EMBY_AUTOPLAY_HOME", str(tmp_path))
    monkeypatch.setenv("EMBY_SYSTEMD_UNIT_DIR", str(unit_dir))
    monkeypatch.syspath_prepend(str(SRC))
    sys.modules.pop("emby_keepalive_systemd_scheduler", None)
    spec = importlib.util.spec_from_file_location(
        "emby_keepalive_systemd_scheduler", SRC / "emby_keepalive_systemd_scheduler.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, unit_dir


class Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_scheduler_writes_persistent_systemd_units(tmp_path, monkeypatch):
    scheduler, unit_dir = load_scheduler(tmp_path, monkeypatch)
    calls = []

    def fake_run(cmd, capture_output=False, text=False):
        calls.append(cmd)
        if cmd[:2] == ["systemctl", "daemon-reload"]:
            return Result()
        if cmd[:3] == ["systemctl", "enable", "--now"]:
            return Result(stdout="Created symlink")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(scheduler.subprocess, "run", fake_run)

    unit_name, out = scheduler.schedule_systemd_run(
        datetime(2026, 7, 25, 6, 14, 8, tzinfo=timezone.utc), 355
    )

    assert unit_name == "emby-keepalive-20260725T061408Z"
    assert "wrote" in out
    service = (unit_dir / f"{unit_name}.service").read_text(encoding="utf-8")
    timer = (unit_dir / f"{unit_name}.timer").read_text(encoding="utf-8")
    assert "Environment=EMBY_PLAY_SECONDS=355" in service
    assert f"ExecStart={tmp_path}/emby_keepalive_systemd_runner.sh" in service
    assert "OnCalendar=2026-07-25 06:14:08 UTC" in timer
    assert "Persistent=true" in timer
    assert f"Unit={unit_name}.service" in timer
    assert ["systemctl", "daemon-reload"] in calls
    assert ["systemctl", "enable", "--now", f"{unit_name}.timer"] in calls


def test_scheduler_recreates_missing_recorded_timer(tmp_path, monkeypatch):
    scheduler, unit_dir = load_scheduler(tmp_path, monkeypatch)
    state_path = tmp_path / "emby_keepalive_state.json"
    stale_service = unit_dir / "emby-keepalive-20260607T070547Z.service"
    stale_timer = unit_dir / "emby-keepalive-20260607T070547Z.timer"
    stale_service.write_text("stale", encoding="utf-8")
    stale_timer.write_text("stale", encoding="utf-8")
    state_path.write_text(
        json.dumps(
            {
                "enabled": True,
                "last_run_at": None,
                "last_status": None,
                "last_duration_seconds": None,
                "next_run_at": "2026-06-07T07:05:47Z",
                "next_duration_seconds": 348,
                "next_unit_name": "emby-keepalive-20260607T070547Z",
                "created_at": "2026-03-22T10:49:25Z",
                "updated_at": "2026-05-13T10:09:50Z",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    calls = []

    def fake_run(cmd, capture_output=False, text=False):
        calls.append(cmd)
        if cmd[:3] == ["systemctl", "show", "emby-keepalive-20260607T070547Z.timer"]:
            return Result(returncode=0, stdout="loaded\n/run/systemd/transient/emby-keepalive-20260607T070547Z.timer\n")
        if cmd[:2] == ["systemctl", "daemon-reload"]:
            return Result()
        if cmd[:3] == ["systemctl", "enable", "--now"]:
            return Result(stdout="Created symlink")
        if cmd[:3] == ["systemctl", "disable", "--now"]:
            return Result()
        if cmd[:2] in (["systemctl", "stop"], ["systemctl", "reset-failed"]):
            return Result()
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(scheduler.subprocess, "run", fake_run)
    monkeypatch.setattr(
        scheduler,
        "next_schedule_from",
        lambda base: datetime(2026, 7, 25, 6, 14, 8, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(scheduler, "weighted_duration_seconds", lambda: 355)

    assert scheduler.main() == 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["next_unit_name"] == "emby-keepalive-20260725T061408Z"
    assert state["next_run_at"] == "2026-07-25T06:14:08Z"
    assert state["next_duration_seconds"] == 355
    assert not stale_service.exists()
    assert not stale_timer.exists()
    assert (unit_dir / "emby-keepalive-20260725T061408Z.service").exists()
    assert (unit_dir / "emby-keepalive-20260725T061408Z.timer").exists()
    log = (tmp_path / "logs" / "emby_keepalive_scheduler.log").read_text(encoding="utf-8")
    assert "Missing timer detected for recorded unit=emby-keepalive-20260607T070547Z" in log
    assert "Scheduled next run: unit=emby-keepalive-20260725T061408Z" in log
    assert any(cmd[:3] == ["systemctl", "show", "emby-keepalive-20260607T070547Z.timer"] for cmd in calls)
    assert any(cmd[:3] == ["systemctl", "disable", "--now"] for cmd in calls)


def test_keepalive_uses_browser_like_json_headers():
    keepalive = (SRC / "emby_keepalive.py").read_text(encoding="utf-8")
    assert "'Accept': 'application/json, text/plain, */*'" in keepalive
    assert "'User-Agent': 'Mozilla/5.0" in keepalive


def test_uninstall_removes_persistent_units():
    uninstall = (REPO / "uninstall.sh").read_text(encoding="utf-8")
    assert 'systemctl disable --now "$unit_name.timer"' in uninstall
    assert 'rm -f "/etc/systemd/system/$unit_name.timer" "/etc/systemd/system/$unit_name.service"' in uninstall
    assert "systemctl daemon-reload" in uninstall
