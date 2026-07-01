#!/usr/bin/env python3
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from emby_keepalive_config import parse_env, timing_settings

BASE_DIR = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
STATE_PATH = os.path.join(BASE_DIR, 'emby_keepalive_state.json')
RUNNER = os.path.join(BASE_DIR, 'emby_keepalive_systemd_runner.sh')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'emby_keepalive_scheduler.log')
SYSTEMD_UNIT_DIR = os.environ.get('EMBY_SYSTEMD_UNIT_DIR', '/etc/systemd/system')
UNIT_PREFIX = 'emby-keepalive'
CFG = parse_env()
TIMING = timing_settings(CFG)

MIN_DAYS = TIMING['min_days']
MAX_DAYS = TIMING['max_days']
MIN_SECONDS = TIMING['min_seconds']
SOFT_MAX_SECONDS = TIMING['soft_max_seconds']
HARD_MAX_SECONDS = TIMING['hard_max_seconds']
PREFER_SOFT_MAX_PROB = TIMING['prefer_soft_max_prob']


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def weighted_duration_seconds():
    if HARD_MAX_SECONDS <= SOFT_MAX_SECONDS or random.random() < PREFER_SOFT_MAX_PROB:
        return random.randint(MIN_SECONDS, SOFT_MAX_SECONDS)
    return random.randint(SOFT_MAX_SECONDS + 1, HARD_MAX_SECONDS)


def next_schedule_from(base_time):
    days = random.randint(MIN_DAYS, MAX_DAYS)
    target_day = (base_time + timedelta(days=days)).date()
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime(target_day.year, target_day.month, target_day.day, hour, minute, second, tzinfo=timezone.utc)


def load_state():
    if not os.path.exists(STATE_PATH):
        return None
    try:
        with open(STATE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log_line(f'WARNING: state file unreadable, resetting: {STATE_PATH} ({e})')
        return None


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def log_line(text):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def sanitize_unit_suffix(ts):
    return ts.strftime('%Y%m%dT%H%M%SZ')


def systemd_escape_value(value):
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def write_atomic(path, content):
    tmp = f'{path}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(content)
    os.replace(tmp, path)


def run_systemctl(*args):
    result = subprocess.run(['systemctl', *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'systemctl {" ".join(args)} failed: {result.stderr.strip() or result.stdout.strip()}')
    return result.stdout.strip()


def schedule_systemd_run(run_at, duration_seconds):
    unit_name = f'{UNIT_PREFIX}-{sanitize_unit_suffix(run_at)}'
    service_path = os.path.join(SYSTEMD_UNIT_DIR, f'{unit_name}.service')
    timer_path = os.path.join(SYSTEMD_UNIT_DIR, f'{unit_name}.timer')
    run_at_text = run_at.strftime('%Y-%m-%d %H:%M:%S UTC')
    description = f'Random Emby keepalive at {iso(run_at)}'
    service_content = f'''[Unit]\nDescription={description}\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nType=oneshot\nEnvironment=EMBY_AUTOPLAY_HOME={systemd_escape_value(BASE_DIR)}\nEnvironment=EMBY_PLAY_SECONDS={int(duration_seconds)}\nExecStart={systemd_escape_value(RUNNER)}\n'''
    timer_content = f'''[Unit]\nDescription={description}\n\n[Timer]\nOnCalendar={run_at_text}\nPersistent=true\nUnit={unit_name}.service\n\n[Install]\nWantedBy=timers.target\n'''
    write_atomic(service_path, service_content)
    write_atomic(timer_path, timer_content)
    run_systemctl('daemon-reload')
    enable_out = run_systemctl('enable', '--now', f'{unit_name}.timer')
    return unit_name, f'wrote {service_path} {timer_path}; {enable_out}'


def cleanup_unit(unit_name):
    if not unit_name:
        return
    subprocess.run(['systemctl', 'disable', '--now', f'{unit_name}.timer'], capture_output=True, text=True)
    subprocess.run(['systemctl', 'stop', f'{unit_name}.service'], capture_output=True, text=True)
    subprocess.run(['systemctl', 'reset-failed', f'{unit_name}.timer', f'{unit_name}.service'], capture_output=True, text=True)
    for suffix in ('timer', 'service'):
        try:
            os.remove(os.path.join(SYSTEMD_UNIT_DIR, f'{unit_name}.{suffix}'))
        except FileNotFoundError:
            pass
    subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, text=True)


def unit_timer_exists(unit_name):
    result = subprocess.run(
        ['systemctl', 'show', f'{unit_name}.timer', '--property=LoadState,FragmentPath', '--value'],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    values = result.stdout.splitlines()
    load_state = values[0].strip() if values else ''
    fragment_path = values[1].strip() if len(values) > 1 else ''
    if load_state != 'loaded':
        return False
    expected_path = os.path.join(SYSTEMD_UNIT_DIR, f'{unit_name}.timer')
    if os.path.abspath(fragment_path) != os.path.abspath(expected_path):
        log_line(
            f'Existing timer for unit={unit_name} is not persistent at expected path '
            f'{expected_path} (fragment={fragment_path or "none"}); recreating it'
        )
        return False
    return True


def ensure_state(state, current_time):
    if state:
        return state
    return {
        'enabled': True,
        'last_run_at': None,
        'last_status': None,
        'last_duration_seconds': None,
        'next_run_at': None,
        'next_duration_seconds': None,
        'next_unit_name': None,
        'created_at': iso(current_time),
        'updated_at': iso(current_time),
    }


def plan_next(state, base_time):
    next_run = next_schedule_from(base_time)
    duration = weighted_duration_seconds()
    unit_name, out = schedule_systemd_run(next_run, duration)
    state['next_run_at'] = iso(next_run)
    state['next_duration_seconds'] = duration
    state['next_unit_name'] = unit_name
    state['updated_at'] = iso(now_utc())
    save_state(state)
    log_line(f'Scheduled next run: unit={unit_name} next_run_at={state["next_run_at"]} duration={duration}s result={out}')


def main():
    current_time = now_utc()
    state = ensure_state(load_state(), current_time)

    if not state.get('enabled', True):
        print('Scheduler disabled')
        save_state(state)
        return 0

    if state.get('last_status') == 'running':
        log_line(
            'WARNING: previous run left status=running (runner likely crashed); '
            'marking last_status=unknown and clearing stale schedule pointers'
        )
        state['last_status'] = 'unknown'
        state['last_run_at'] = iso(current_time)
        state['last_duration_seconds'] = state.get('next_duration_seconds')
        state['next_run_at'] = None
        state['next_duration_seconds'] = None
        state['next_unit_name'] = None

    if state.get('next_run_at') and state.get('next_unit_name'):
        if not unit_timer_exists(state['next_unit_name']):
            missing_unit = state['next_unit_name']
            log_line(
                f'Missing timer detected for recorded unit={missing_unit}; '
                'clearing stale schedule state and recreating it'
            )
            cleanup_unit(missing_unit)
            state['next_run_at'] = None
            state['next_duration_seconds'] = None
            state['next_unit_name'] = None
            state['updated_at'] = iso(current_time)
            save_state(state)
        else:
            print(f'Already scheduled: unit={state["next_unit_name"]} next_run_at={state["next_run_at"]} duration={state["next_duration_seconds"]}')
            save_state(state)
            return 0

    try:
        plan_next(state, current_time)
    except RuntimeError as e:
        log_line(f'ERROR: failed to schedule next run: {e}')
        print(f'ERROR: failed to schedule next run: {e}', file=sys.stderr)
        return 1
    print(f'Scheduled: unit={state["next_unit_name"]} next_run_at={state["next_run_at"]} duration={state["next_duration_seconds"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
