#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone

BASE_DIR = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
HISTORY_PATH = os.path.join(BASE_DIR, 'emby_keepalive_history.json')
MAX_HISTORY = 20


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_history(items):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    items = items[:MAX_HISTORY]
    tmp = HISTORY_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HISTORY_PATH)


def add_history(item_id, name):
    history = load_history()
    history.insert(0, {'item_id': str(item_id), 'name': name, 'played_at': now_iso()})
    save_history(history)


def recent_item_ids(limit=5):
    return {str(x.get('item_id')) for x in load_history()[:limit] if x.get('item_id')}
