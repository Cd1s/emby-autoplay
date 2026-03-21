#!/usr/bin/env python3
import json
import os
import subprocess
from getpass import getpass
from pathlib import Path

from emby_keepalive_config import save_env, parse_env

BASE_DIR = Path(os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay'))
STATE_PATH = BASE_DIR / 'emby_keepalive_state.json'
SCHEDULER = BASE_DIR / 'emby_keepalive_systemd_scheduler.py'


def input_default(prompt, default=''):
    val = input(f'{prompt} [{default}]: ').strip()
    return val if val else default


def main():
    cfg = parse_env()
    print('=== Emby Autoplay Interactive Setup ===')
    cfg['EMBY_SCHEME'] = input_default('Protocol (http/https)', cfg.get('EMBY_SCHEME', 'http'))
    cfg['EMBY_HOST'] = input_default('Host / domain', cfg.get('EMBY_HOST', ''))
    cfg['EMBY_PORT'] = input_default('Port', cfg.get('EMBY_PORT', '8096'))
    cfg['EMBY_USERNAME'] = input_default('Username', cfg.get('EMBY_USERNAME', ''))
    pwd = getpass('Password [hidden]: ').strip()
    if pwd:
        cfg['EMBY_PASSWORD'] = pwd
    cfg['EMBY_MIN_DAYS'] = input_default('Min days between runs', cfg.get('EMBY_MIN_DAYS', '22'))
    cfg['EMBY_MAX_DAYS'] = input_default('Max days between runs', cfg.get('EMBY_MAX_DAYS', '28'))
    cfg['EMBY_MIN_PLAY_SECONDS'] = input_default('Min play seconds (>300)', cfg.get('EMBY_MIN_PLAY_SECONDS', '301'))
    cfg['EMBY_SOFT_MAX_PLAY_SECONDS'] = input_default('Preferred soft max play seconds', cfg.get('EMBY_SOFT_MAX_PLAY_SECONDS', '600'))
    cfg['EMBY_HARD_MAX_PLAY_SECONDS'] = input_default('Hard max play seconds (<1200)', cfg.get('EMBY_HARD_MAX_PLAY_SECONDS', '1199'))
    cfg['EMBY_PREFER_SOFT_MAX_PROB'] = input_default('Probability of staying within soft max (0-1)', cfg.get('EMBY_PREFER_SOFT_MAX_PROB', '0.85'))
    cfg['EMBY_VERIFY_SSL'] = input_default('Verify SSL (true/false)', cfg.get('EMBY_VERIFY_SSL', 'true'))
    cfg['EMBY_TIMEOUT'] = input_default('HTTP timeout seconds', cfg.get('EMBY_TIMEOUT', '30'))

    save_env(cfg)

    if not STATE_PATH.exists():
        now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
        STATE_PATH.write_text(json.dumps({
            'enabled': True,
            'last_run_at': None,
            'last_status': None,
            'last_duration_seconds': None,
            'next_run_at': None,
            'next_duration_seconds': None,
            'next_unit_name': None,
            'created_at': now,
            'updated_at': now,
        }, ensure_ascii=False, indent=2), encoding='utf-8')

    print('\nConfig saved. Scheduling next run...')
    subprocess.run(['python3', str(SCHEDULER)], check=False)
    print('Done.')


if __name__ == '__main__':
    main()
