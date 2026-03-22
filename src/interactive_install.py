#!/usr/bin/env python3
import json
import os
import subprocess
from getpass import getpass, GetPassWarning
from pathlib import Path
import warnings

from emby_keepalive_config import save_env, parse_env

BASE_DIR = Path(os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay'))
STATE_PATH = BASE_DIR / 'emby_keepalive_state.json'
SCHEDULER = BASE_DIR / 'emby_keepalive_systemd_scheduler.py'


def input_default(prompt, default=''):
    val = input(f'{prompt} [{default}]: ').strip()
    return val if val else default


def choose_scheme(default='http'):
    default = default if default in ('http', 'https') else 'http'
    while True:
        print('\n选择协议：')
        print('  1) http')
        print('  2) https')
        raw = input(f'请输入 1 或 2，直接回车默认 [{default}]: ').strip().lower()
        if not raw:
            return default
        if raw == '1':
            return 'http'
        if raw == '2':
            return 'https'
        if raw in ('http', 'https'):
            return raw
        print('输入无效，请重新选择。')


def input_bool(prompt, default='true'):
    while True:
        raw = input(f'{prompt} [默认 {default}] (true/false): ').strip().lower()
        if not raw:
            return default
        if raw in ('true', 'false'):
            return raw
        print('请输入 true 或 false。')


def reset_state():
    now = __import__('datetime').datetime.now(__import__('datetime').timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
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


def apply_and_schedule(cfg):
    save_env(cfg)
    reset_state()
    print('\n配置已保存，正在预约下一次运行...')
    subprocess.run(['python3', str(SCHEDULER)], check=False)
    print('完成。你现在可以运行：embyautoplay')


def env_override(cfg, key, env_name):
    val = os.environ.get(env_name)
    if val is not None and val != '':
        cfg[key] = val


def maybe_non_interactive(cfg):
    auto = os.environ.get('EMBY_AUTOPLAY_AUTO_SETUP', '').lower() in ('1', 'true', 'yes')
    if not auto:
        return False

    env_override(cfg, 'EMBY_SCHEME', 'EMBY_SCHEME')
    env_override(cfg, 'EMBY_HOST', 'EMBY_HOST')
    env_override(cfg, 'EMBY_PORT', 'EMBY_PORT')
    env_override(cfg, 'EMBY_URL', 'EMBY_URL')
    env_override(cfg, 'EMBY_USERNAME', 'EMBY_USERNAME')
    env_override(cfg, 'EMBY_PASSWORD', 'EMBY_PASSWORD')
    env_override(cfg, 'EMBY_MIN_DAYS', 'EMBY_MIN_DAYS')
    env_override(cfg, 'EMBY_MAX_DAYS', 'EMBY_MAX_DAYS')
    env_override(cfg, 'EMBY_MIN_PLAY_SECONDS', 'EMBY_MIN_PLAY_SECONDS')
    env_override(cfg, 'EMBY_SOFT_MAX_PLAY_SECONDS', 'EMBY_SOFT_MAX_PLAY_SECONDS')
    env_override(cfg, 'EMBY_HARD_MAX_PLAY_SECONDS', 'EMBY_HARD_MAX_PLAY_SECONDS')
    env_override(cfg, 'EMBY_PREFER_SOFT_MAX_PROB', 'EMBY_PREFER_SOFT_MAX_PROB')
    env_override(cfg, 'EMBY_VERIFY_SSL', 'EMBY_VERIFY_SSL')
    env_override(cfg, 'EMBY_TIMEOUT', 'EMBY_TIMEOUT')

    print('=== Emby Autoplay 自动配置模式 ===')
    apply_and_schedule(cfg)
    return True


def main():
    cfg = parse_env()
    if maybe_non_interactive(cfg):
        return

    print('=== Emby Autoplay 交互安装 ===')
    print('下面会逐项询问，按回车可使用默认值。\n')

    cfg['EMBY_SCHEME'] = choose_scheme(cfg.get('EMBY_SCHEME', 'http'))
    cfg['EMBY_HOST'] = input_default('请输入 Emby 域名或 IP', cfg.get('EMBY_HOST', ''))
    cfg['EMBY_PORT'] = input_default('请输入端口', cfg.get('EMBY_PORT', '8096'))
    cfg['EMBY_USERNAME'] = input_default('请输入用户名', cfg.get('EMBY_USERNAME', ''))
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=GetPassWarning)
        pwd = getpass('请输入密码（隐藏输入，直接回车保留现有值）: ').strip()
    if pwd:
        cfg['EMBY_PASSWORD'] = pwd

    print('\n=== 随机周期设置 ===')
    cfg['EMBY_MIN_DAYS'] = input_default('最小多少天后运行', cfg.get('EMBY_MIN_DAYS', '22'))
    cfg['EMBY_MAX_DAYS'] = input_default('最大多少天后运行', cfg.get('EMBY_MAX_DAYS', '28'))

    print('\n=== 随机播放时长设置（单位：秒） ===')
    cfg['EMBY_MIN_PLAY_SECONDS'] = input_default('最短播放秒数（>300）', cfg.get('EMBY_MIN_PLAY_SECONDS', '301'))
    cfg['EMBY_SOFT_MAX_PLAY_SECONDS'] = input_default('偏好最长秒数（尽量不超过）', cfg.get('EMBY_SOFT_MAX_PLAY_SECONDS', '600'))
    cfg['EMBY_HARD_MAX_PLAY_SECONDS'] = input_default('硬上限最长秒数（必须小于 1200）', cfg.get('EMBY_HARD_MAX_PLAY_SECONDS', '1199'))
    cfg['EMBY_PREFER_SOFT_MAX_PROB'] = input_default('落在偏好时长内的概率（0~1）', cfg.get('EMBY_PREFER_SOFT_MAX_PROB', '0.85'))

    print('\n=== 网络设置 ===')
    cfg['EMBY_VERIFY_SSL'] = input_bool('是否校验 SSL 证书', cfg.get('EMBY_VERIFY_SSL', 'true'))
    cfg['EMBY_TIMEOUT'] = input_default('HTTP 超时秒数', cfg.get('EMBY_TIMEOUT', '30'))

    apply_and_schedule(cfg)


if __name__ == '__main__':
    main()
