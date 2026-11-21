"""Authorized Qwen32B SSH route (current host port with pinned fingerprint) + upstream gateway.

Adapted on 2026-11-20 from the five-pairs upstream gateway for the current SSH port
10.27.127.9:34218 (host key pinned via the R1 new_host_connection.json receipt).
"""

from contextlib import contextmanager
import http.server
import io
import json
from pathlib import Path
import runpy
import secrets
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request


HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
ROOT = RESULTS.parent
HOST = '10.27.127.9'
SSH_PORT = 34218
MODEL_PORT = 39232
MODEL = 'Qwen3-32B'
QWEN_PROBE = RESULTS / '20261101-longbranch-frontier-pilot-v1/predictor_transport_c1.py'
R1 = RESULTS / '20261119-qwen32b-r1-execution-rl-v1'


def _pin_connect():
    """Connect with the current authorized route: pinned fingerprint, key from session."""
    sys.path.insert(0, str(R1))
    from remote_r1_environment import predictor_key, command  # noqa: F401
    import paramiko

    expected = json.loads((R1 / 'new_host_connection.json').read_text(encoding='utf8'))

    class PinnedHostKey(paramiko.MissingHostKeyPolicy):
        def missing_host_key(self, client, hostname, key):
            observed = 'SHA256:' + __import__('base64').b64encode(
                __import__('hashlib').sha256(key.asbytes()).digest()).decode().rstrip('=')
            if observed != expected['host_key_sha256']:
                raise RuntimeError('SSH host fingerprint mismatch: expected '
                                   + expected['host_key_sha256'] + '; observed ' + observed)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(PinnedHostKey())
    client.connect(expected['host'], port=SSH_PORT, username=expected['username'], pkey=predictor_key(),
                   allow_agent=False, look_for_keys=False, disabled_algorithms={'pubkeys': ['rsa-sha2-512']},
                   timeout=20, auth_timeout=20, banner_timeout=45)
    client.get_transport().set_keepalive(20)
    return client


def model_list(base):
    with urllib.request.urlopen(base + '/models', timeout=15) as response:
        return [row['id'] for row in json.load(response)['data']]


def connection_heartbeat(stop, base):
    """Keep the SSH model route active without invoking model inference."""
    while not stop.is_set():
        receipt = dict(timestamp=time.time(), endpoint='/v1/models', inference_calls=0)
        try:
            models = model_list(base)
            receipt.update(state='passed' if MODEL in models else 'wrong_model', models=models)
        except Exception as error:
            receipt.update(state='failed', error_type=type(error).__name__)
        with (HERE / 'predictor_connection_heartbeat.jsonl').open('a', encoding='utf8') as stream:
            stream.write(json.dumps(receipt, ensure_ascii=False) + '\n')
        if stop.wait(30):
            break


def _tunnel(client):
    sys.path[:0] = [str(ROOT.parent / 'Ofox-MultiBackend5-MockOffer-20261024'),
                    str(Path(tempfile.gettempdir()) / 'semserve-native-h3-paramiko-5')]
    from qwen_experiment_access import start_tunnel

    return start_tunnel(client, MODEL_PORT)


def preflight():
    """Inspect the predictor identity without making an inference."""
    receipt = dict(host=HOST, ssh_port=SSH_PORT, model_port=MODEL_PORT,
                   expected_model=MODEL, model_calls=0)
    try:
        with _pin_connect() as client:
            tunnel, base = _tunnel(client)
            try:
                models = model_list(base)
                receipt.update(models=models, state='passed' if MODEL in models else 'wrong_model')
            except (OSError, ValueError, KeyError) as error:
                receipt.update(state='service_unavailable', error_type=type(error).__name__)
            finally:
                tunnel.shutdown()
                tunnel.server_close()
    except Exception as error:
        receipt.update(state='ssh_unavailable', error_type=type(error).__name__)
    (HERE / 'predictor_preflight.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(receipt, ensure_ascii=False), flush=True)
    return receipt


@contextmanager
def upstream(profile):
    """Expose the original authenticated gateway for the experiment arm."""
    sys.path.insert(0, str(ROOT))
    from user_api_credential import user_api_key

    official = user_api_key(profile['credential_source_user_thread'], profile['credential_fingerprint'])
    auxiliary_source = RESULTS / '20261105-ofox-qwen38-27b-longbranch3-v1/run.py'
    auxiliary = runpy.run_path(str(auxiliary_source))['archived_ofox_key'](
        profile['auxiliary_credential_source_user_thread'])
    with _pin_connect() as client:
        tunnel, base = _tunnel(client)
        gateway = None
        original_request = None
        heartbeat_stop = threading.Event()
        heartbeat = None
        token = secrets.token_urlsafe(32)
        try:
            models = model_list(base)
            if MODEL not in models:
                raise RuntimeError('The frozen Qwen3-32B predictor is unavailable')
            install = runpy.run_path(str(QWEN_PROBE))['install']
            original_request = install(ROOT, HERE / 'predictor-wire-codec.jsonl')

            class Gateway(http.server.BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def forward(self):
                    if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                        self.send_error(401)
                        return
                    if self.path not in ('/v1/models', '/v1/chat/completions'):
                        self.send_error(404)
                        return
                    payload = (self.rfile.read(int(self.headers.get('Content-Length', 0)))
                               if self.command == 'POST' else None)
                    try:
                        request = urllib.request.Request(
                            base.removesuffix('/v1') + self.path, data=payload,
                            headers={'Content-Type': 'application/json'}, method=self.command)
                        with urllib.request.urlopen(request, timeout=190) as response:
                            status, body = response.status, response.read()
                    except urllib.error.HTTPError as error:
                        status, body = error.code, error.read()
                    except (OSError, ValueError):
                        status, body = 502, b'{"error":"qwen_tunnel_unavailable"}'
                    self.send_response(status)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    try:
                        self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

                do_GET = forward
                do_POST = forward

            gateway = http.server.ThreadingHTTPServer(('0.0.0.0', 0), Gateway)
            gateway.daemon_threads = True
            threading.Thread(target=gateway.serve_forever, daemon=True).start()
            heartbeat = threading.Thread(target=connection_heartbeat,
                                         args=(heartbeat_stop, base), daemon=True,
                                         name='qwen-predictor-connection-heartbeat')
            heartbeat.start()
            yield dict(official_key=official, auxiliary_key=auxiliary, gateway_token=token,
                       predictor_base=f'http://host.docker.internal:{gateway.server_port}/v1')
        finally:
            heartbeat_stop.set()
            if heartbeat is not None:
                heartbeat.join(timeout=20)
                if heartbeat.is_alive():
                    client.close()
                    heartbeat.join(timeout=5)
            if gateway is not None:
                gateway.shutdown()
                gateway.server_close()
            if original_request is not None:
                urllib.request.Request = original_request
            tunnel.shutdown()
            tunnel.server_close()


if __name__ == '__main__':
    preflight()
