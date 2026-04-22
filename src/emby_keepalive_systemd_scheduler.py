#!/usr/bin/env python3
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from emby_keepalive_config import parse_env

BASE_DIR = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
STATE_PATH = os.path.join(BASE_DIR, 'emby_keepalive_state.json')
RUNNER = os.path.join(BASE_DIR, 'emby_keepalive_systemd_runner.sh')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'emby_keepalive_scheduler.log')
UNIT_PREFIX = 'emby-keepalive'
CFG = parse_env()

MIN_DAYS = int(CFG.get('EMBY_MIN_DAYS', '22'))
MAX_DAYS = int(CFG.get('EMBY_MAX_DAYS', '28'))
MIN_SECONDS = int(CFG.get('EMBY_MIN_PLAY_SECONDS', '301'))
SOFT_MAX_SECONDS = int(CFG.get('EMBY_SOFT_MAX_PLAY_SECONDS', '600'))
HARD_MAX_SECONDS = int(CFG.get('EMBY_HARD_MAX_PLAY_SECONDS', '1199'))
PREFER_SOFT_MAX_PROB = float(CFG.get('EMBY_PREFER_SOFT_MAX_PROB', '0.85'))


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def weighted_duration_seconds():
    if random.random() < PREFER_SOFT_MAX_PROB:
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
    except json.JSONDecodeError:
        log_line(f'WARNING: state file corrupted, resetting: {STATE_PATH}')
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


def schedule_systemd_run(run_at, duration_seconds):
    unit_name = f'{UNIT_PREFIX}-{sanitize_unit_suffix(run_at)}'
    result = subprocess.run([
        'systemd-run',
        '--unit', unit_name,
        '--description', f'Random Emby keepalive at {iso(run_at)}',
        '--on-calendar', run_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
        '--property=Type=oneshot',
        '--setenv', f'EMBY_PLAY_SECONDS={duration_seconds}',
        RUNNER,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'systemd-run failed: {result.stderr.strip() or result.stdout.strip()}')
    return unit_name, result.stdout.strip()


def unit_timer_exists(unit_name):
    result = subprocess.run(
        ['systemctl', 'status', f'{unit_name}.timer', '--no-pager'],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


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
        state['last_status'] = 'success'
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
