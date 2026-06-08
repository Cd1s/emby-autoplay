import importlib.util
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class FakeResponse:
    def __init__(self, data=None, status_code=200):
        self._data = data or {}
        self.status_code = status_code

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            exc = requests.HTTPError(f'{self.status_code} error')
            exc.response = self
            raise exc


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def close(self):
        self.closed = True


def load_keepalive() -> Any:
    os.environ.update({
        'EMBY_AUTOPLAY_HOME': '/tmp/emby-autoplay-test',
        'EMBY_URL': 'http://emby.test:8096',
        'EMBY_USERNAME': 'user',
        'EMBY_PASSWORD': 'password',
        'EMBY_PLAY_SECONDS': '1',
        'EMBY_RETRY_ATTEMPTS': '1',
        'EMBY_RETRY_BACKOFF_SECONDS': '0',
    })
    name = 'emby_keepalive_under_test'
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, SRC / 'emby_keepalive.py')
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.RETRY_BACKOFF_SECONDS = 0
    return module


class EmbyKeepaliveTests(unittest.TestCase):
    def test_req_retries_transient_timeout(self):
        mod = load_keepalive()
        mod.RETRY_ATTEMPTS = 2
        session = FakeSession([
            mod.requests.Timeout('temporary timeout'),
            FakeResponse({'ok': True}),
        ])

        with redirect_stderr(io.StringIO()):
            response = mod.req(session, 'GET', '/System/Info')

        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(len(session.calls), 2)

    def test_main_sends_failed_stop_after_progress_error(self):
        mod = load_keepalive()
        mod.RETRY_ATTEMPTS = 1
        mod.time.sleep = lambda _seconds: None
        mod.recent_item_ids = lambda _limit=8: set()
        mod.add_history = lambda _item_id, _name: None

        session = FakeSession([
            FakeResponse({'User': {'Id': 'u1'}, 'AccessToken': 'token', 'SessionInfo': {'Id': 's1'}}),
            FakeResponse(),
            FakeResponse({'TotalRecordCount': 1}),
            FakeResponse({'Items': [{
                'Id': 'item1',
                'Name': 'Movie',
                'MediaSources': [{'Id': 'ms1'}],
                'RunTimeTicks': 600_000_000,
            }]}),
            FakeResponse({'PlaySessionId': 'play1'}),
            FakeResponse(),
            mod.requests.ConnectionError('progress failed'),
            FakeResponse(),
        ])
        mod.requests.Session = lambda: session

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(mod.requests.ConnectionError):
                mod.main()

        stopped_calls = [
            call for call in session.calls
            if call[1].endswith('/Sessions/Playing/Stopped')
        ]
        self.assertEqual(len(stopped_calls), 1)
        payload = stopped_calls[0][2]['json']
        self.assertTrue(payload['Failed'])
        self.assertEqual(payload['PositionTicks'], 10_000_000)
        self.assertTrue(session.closed)


if __name__ == '__main__':
    unittest.main()
