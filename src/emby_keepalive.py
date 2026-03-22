#!/usr/bin/env python3
import os
import sys
import time
import random
import requests
from emby_keepalive_config import parse_env
from emby_keepalive_history import add_history, recent_item_ids

BASE_DIR = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
CFG = parse_env()
BASE_URL = os.environ.get('EMBY_URL', CFG.get('EMBY_URL', '')).rstrip('/')
USERNAME = os.environ.get('EMBY_USERNAME', CFG.get('EMBY_USERNAME', ''))
PASSWORD = os.environ.get('EMBY_PASSWORD', CFG.get('EMBY_PASSWORD', ''))
PLAY_SECONDS = int(os.environ.get('EMBY_PLAY_SECONDS', '120'))
DEVICE_ID = os.environ.get('EMBY_DEVICE_ID', CFG.get('EMBY_DEVICE_ID', 'emby-autoplay'))
CLIENT_NAME = os.environ.get('EMBY_CLIENT_NAME', CFG.get('EMBY_CLIENT_NAME', 'EmbyAutoplay'))
CLIENT_VERSION = os.environ.get('EMBY_CLIENT_VERSION', CFG.get('EMBY_CLIENT_VERSION', '1.0.0'))
VERIFY_SSL = os.environ.get('EMBY_VERIFY_SSL', CFG.get('EMBY_VERIFY_SSL', 'true')).lower() not in ('0', 'false', 'no')
REQUEST_TIMEOUT = int(os.environ.get('EMBY_TIMEOUT', CFG.get('EMBY_TIMEOUT', '30')))

if not BASE_URL or not USERNAME or not PASSWORD:
    print('Missing EMBY_URL / EMBY_USERNAME / EMBY_PASSWORD', file=sys.stderr)
    sys.exit(2)

AUTH_HEADER = (
    f'MediaBrowser Client="{CLIENT_NAME}", '
    f'Device="EmbyAutoplay", DeviceId="{DEVICE_ID}", Version="{CLIENT_VERSION}"'
)

DEVICE_PROFILE = {
    'Name': 'Chrome',
    'MaxStreamingBitrate': 40000000,
    'MusicStreamingTranscodingBitrate': 192000,
    'TimelineOffsetSeconds': 5,
    'DirectPlayProfiles': [
        {'Container': 'mp4,m4v,mkv,ts,mpegts', 'Type': 'Video'},
        {'Container': 'mp3,aac,m4a,flac,ogg,wav', 'Type': 'Audio'},
    ],
    'TranscodingProfiles': [],
    'ContainerProfiles': [],
    'CodecProfiles': [],
    'SubtitleProfiles': [
        {'Format': 'srt', 'Method': 'External'},
        {'Format': 'ass', 'Method': 'External'},
        {'Format': 'vtt', 'Method': 'External'},
    ],
}


def req(session, method, path, **kwargs):
    url = BASE_URL + path
    kwargs.setdefault('timeout', REQUEST_TIMEOUT)
    kwargs.setdefault('verify', VERIFY_SSL)
    r = session.request(method, url, **kwargs)
    r.raise_for_status()
    return r


def main():
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json',
        'X-Emby-Authorization': AUTH_HEADER,
    })

    auth = req(session, 'POST', '/Users/AuthenticateByName', json={
        'Username': USERNAME,
        'Pw': PASSWORD,
    }).json()

    user_id = auth['User']['Id']
    access_token = auth['AccessToken']
    session_id = auth.get('SessionInfo', {}).get('Id')
    session.headers.update({'X-Emby-Token': access_token})

    req(session, 'POST', '/Sessions/Capabilities/Full', json={
        'PlayableMediaTypes': ['Video'],
        'SupportsMediaControl': True,
        'SupportsPersistentIdentifier': False,
    })

    items = req(
        session,
        'GET',
        f'/Users/{user_id}/Items?Recursive=true&IncludeItemTypes=Movie,Episode&Limit=200&Fields=MediaSources,RunTimeTicks'
    ).json().get('Items', [])

    playable = [i for i in items if i.get('MediaSources')]
    if not playable:
        print('No playable items found', file=sys.stderr)
        sys.exit(3)

    recent_ids = recent_item_ids(8)
    filtered = [i for i in playable if str(i.get('Id')) not in recent_ids]
    candidate_pool = filtered or playable
    item = random.choice(candidate_pool)
    media_source_id = item['MediaSources'][0]['Id']
    item_id = item['Id']
    runtime_ticks = int(item.get('RunTimeTicks') or 0)
    target_ticks = min(PLAY_SECONDS * 10_000_000, runtime_ticks or PLAY_SECONDS * 10_000_000)

    playback_info = req(
        session,
        'POST',
        f'/Items/{item_id}/PlaybackInfo',
        json={
            'DeviceProfile': DEVICE_PROFILE,
            'UserId': user_id,
            'StartTimeTicks': 0,
            'IsPlayback': True,
            'AutoOpenLiveStream': True,
            'MediaSourceId': media_source_id,
            'EnableDirectPlay': True,
            'EnableDirectStream': True,
        },
    ).json()

    play_session_id = playback_info.get('PlaySessionId')
    if not play_session_id:
        print('PlaybackInfo did not return PlaySessionId', file=sys.stderr)
        sys.exit(4)

    print(f'Authenticated as {USERNAME}; session={session_id or "unknown"}')
    print(f'Playing item: {item.get("Name")} (ItemId={item_id}, MediaSourceId={media_source_id})')
    print(f'PlaySessionId: {play_session_id}')

    common_payload = {
        'CanSeek': True,
        'ItemId': item_id,
        'MediaSourceId': media_source_id,
        'IsPaused': False,
        'IsMuted': False,
        'PlayMethod': 'DirectPlay',
        'PlaySessionId': play_session_id,
        'PlaylistIndex': 0,
        'PlaylistLength': 1,
        'RepeatMode': 'RepeatNone',
        'VolumeLevel': 100,
    }

    req(session, 'POST', '/Sessions/Playing', json={
        **common_payload,
        'PositionTicks': 0,
    })

    step = 30
    current = 0
    while current < PLAY_SECONDS:
        current = min(current + step, PLAY_SECONDS)
        position_ticks = min(current * 10_000_000, target_ticks)
        req(session, 'POST', '/Sessions/Playing/Progress', json={
            **common_payload,
            'PositionTicks': position_ticks,
            'EventName': 'timeupdate',
        })
        print(f'Progress reported: {current}s')
        if current < PLAY_SECONDS:
            time.sleep(step)

    req(session, 'POST', '/Sessions/Playing/Stopped', json={
        **common_payload,
        'PositionTicks': target_ticks,
        'Failed': False,
    })

    verify = req(session, 'GET', f'/Users/{user_id}/Items/{item_id}?Fields=UserData,RunTimeTicks').json()
    add_history(item_id, item.get('Name') or '')
    print('UserData:', verify.get('UserData'))
    print('Stopped cleanly.')


if __name__ == '__main__':
    main()
