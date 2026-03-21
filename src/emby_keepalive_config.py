#!/usr/bin/env python3
import os
from urllib.parse import urlparse

BASE_DIR = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
ENV_PATH = os.path.join(BASE_DIR, 'emby_keepalive.env')

DEFAULTS = {
    'EMBY_SCHEME': 'http',
    'EMBY_HOST': '',
    'EMBY_PORT': '8096',
    'EMBY_URL': '',
    'EMBY_USERNAME': '',
    'EMBY_PASSWORD': '',
    'EMBY_DEVICE_ID': 'emby-autoplay',
    'EMBY_CLIENT_NAME': 'EmbyAutoplay',
    'EMBY_CLIENT_VERSION': '1.0.0',
    'EMBY_VERIFY_SSL': 'true',
    'EMBY_TIMEOUT': '30',
    'EMBY_MIN_DAYS': '22',
    'EMBY_MAX_DAYS': '28',
    'EMBY_MIN_PLAY_SECONDS': '301',
    'EMBY_SOFT_MAX_PLAY_SECONDS': '600',
    'EMBY_HARD_MAX_PLAY_SECONDS': '1199',
    'EMBY_PREFER_SOFT_MAX_PROB': '0.85',
    'EMBY_PLAY_SECONDS_DEFAULT': '300',
}

ORDER = [
    'EMBY_SCHEME', 'EMBY_HOST', 'EMBY_PORT', 'EMBY_URL',
    'EMBY_USERNAME', 'EMBY_PASSWORD',
    'EMBY_DEVICE_ID', 'EMBY_CLIENT_NAME', 'EMBY_CLIENT_VERSION',
    'EMBY_VERIFY_SSL', 'EMBY_TIMEOUT',
    'EMBY_MIN_DAYS', 'EMBY_MAX_DAYS',
    'EMBY_MIN_PLAY_SECONDS', 'EMBY_SOFT_MAX_PLAY_SECONDS', 'EMBY_HARD_MAX_PLAY_SECONDS',
    'EMBY_PREFER_SOFT_MAX_PROB', 'EMBY_PLAY_SECONDS_DEFAULT'
]


def shell_quote(val: str) -> str:
    return "'" + val.replace("'", "'\"'\"'") + "'"


def parse_env(path=ENV_PATH):
    data = DEFAULTS.copy()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                v = v.strip()
                if len(v) >= 2 and ((v[0] == v[-1] == "'") or (v[0] == v[-1] == '"')):
                    v = v[1:-1]
                data[k.strip()] = v
    if not data.get('EMBY_URL') and data.get('EMBY_HOST'):
        data['EMBY_URL'] = build_url(data)
    else:
        hydrate_from_url(data)
    return data


def build_url(data):
    scheme = data.get('EMBY_SCHEME', 'http').strip() or 'http'
    host = data.get('EMBY_HOST', '').strip()
    port = str(data.get('EMBY_PORT', '')).strip()
    if not host:
        return data.get('EMBY_URL', '').strip()
    return f'{scheme}://{host}:{port}' if port else f'{scheme}://{host}'


def hydrate_from_url(data):
    url = (data.get('EMBY_URL') or '').strip()
    if not url:
        return
    p = urlparse(url)
    if p.scheme:
        data['EMBY_SCHEME'] = p.scheme
    if p.hostname:
        data['EMBY_HOST'] = p.hostname
    if p.port:
        data['EMBY_PORT'] = str(p.port)
    elif not data.get('EMBY_PORT'):
        data['EMBY_PORT'] = '443' if p.scheme == 'https' else '80'


def save_env(data, path=ENV_PATH):
    data = dict(data)
    data['EMBY_URL'] = build_url(data)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for key in ORDER:
            f.write(f'{key}={shell_quote(str(data.get(key, "")))}\n')
