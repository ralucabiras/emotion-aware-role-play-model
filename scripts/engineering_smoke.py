"""Run the compiled offline app against a disposable real MongoDB database.

Requires backend dependencies, frontend npm ci, and Playwright Chromium.
Only child backend processes created here are restarted. No Docker required.
"""
import functools
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]


class SPA(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not Path(self.translate_path(self.path)).is_file():
            self.path = '/index.html'
        super().do_GET()

    def log_message(self, *_args):
        pass


def ready():
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with urlopen('http://localhost:18000/api/health/ready', timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(.25)
    raise RuntimeError('Backend readiness timed out; see backend log.')


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    for port in (18000, 15173):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    database = 'affectlab_engineering_' + uuid4().hex
    mongo = MongoClient(os.environ.get('TEST_MONGODB_URI', 'mongodb://localhost:27017'), serverSelectionTimeoutMS=5000)
    mongo.admin.command('ping')
    mongo_version = mongo.server_info()['version']
    env = {**os.environ, 'ENVIRONMENT': 'development', 'PERSISTENCE_BACKEND': 'mongo',
           'MONGODB_URI': os.environ.get('TEST_MONGODB_URI', 'mongodb://localhost:27017'),
           'MONGODB_DATABASE': database, 'FRONTEND_ORIGIN': 'http://localhost:15173',
           'CORS_ALLOWED_ORIGINS': 'http://localhost:15173', 'TRUSTED_HOSTS': 'localhost,127.0.0.1',
           'ENFORCE_HTTPS': 'false', 'JWT_SECRET': 'isolated-engineering-smoke-secret-32-bytes',
           'OFFLINE_DEMO_MODE': 'true', 'OFFLINE_DEMO_EMAIL': 'smoke-researcher@example.com',
           'OFFLINE_DEMO_PASSWORD': 'full-stack-smoke-password', 'RESEARCHER_EMAILS': 'smoke-researcher@example.com',
           'PILOT_ACCESS_CODE': 'smoke-pilot-code', 'PILOT_STUDY_LABEL': 'AffectLab pilot study',
           'STUDY_PARTICIPANT_TARGET': '1', 'STUDY_COMPLETER_TARGET': '1', 'OPENAI_API_KEY': '', 'OPENAI_ROLEPLAY_ENABLED': 'false',
           'TRANSCRIPTION_ENABLED': 'false', 'MULTIMODAL_INFERENCE_ENABLED': 'false',
           'SMTP_HOST': '', 'RATE_LIMIT_ENABLED': 'false', 'VITE_API_URL': 'http://localhost:18000/api',
           'FULL_STACK_API_URL': 'http://localhost:18000/api', 'FULL_STACK_BASE_URL': 'http://localhost:15173'}
    frontend = ROOT / 'frontend'
    subprocess.run(['node', 'node_modules/typescript/bin/tsc', '-b'], cwd=frontend, env=env, check=True)
    subprocess.run(['node', 'node_modules/vite/bin/vite.js', 'build'], cwd=frontend, env=env, check=True)
    output = ROOT / 'docs/evidence-package/generated'
    output.mkdir(parents=True, exist_ok=True)
    env['AFFECTLAB_EVIDENCE_DIR'] = str(output)
    logs = ROOT / '.local/engineering-smoke'
    logs.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 15173), functools.partial(SPA, directory=str(frontend / 'dist')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    backend = browser = None
    restarts = []
    started = time.monotonic()
    result = 1
    with tempfile.TemporaryDirectory(prefix='affectlab-engineering-') as control:
        env['FULL_STACK_CONTROL_DIR'] = control
        with open(logs / 'backend-smoke.log', 'w', encoding='utf-8') as log:
            def launch():
                return subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '18000'], cwd=ROOT / 'backend', env=env, stdout=log, stderr=log)
            try:
                backend = launch()
                ready()
                browser = subprocess.Popen(['node', 'node_modules/@playwright/test/cli.js', 'test', '--config=playwright.fullstack.config.ts'], cwd=frontend, env=env)
                request = Path(control) / 'restart.request'
                while browser.poll() is None:
                    if request.exists():
                        request_id = request.read_text()
                        request.unlink()
                        old_pid = backend.pid
                        stop(backend)
                        backend = launch()
                        ready()
                        restarts.append({'old_pid': old_pid, 'new_pid': backend.pid})
                        (Path(control) / 'restart.response').write_text(request_id)
                    time.sleep(.1)
                result = browser.returncode
            finally:
                stop(browser)
                stop(backend)
                server.shutdown()
                server.server_close()
                # Exact freshly generated name; never accept a database name from input.
                mongo.drop_database(database)
                mongo.close()
                (output / 'smoke-v1.json').write_text(json.dumps({'version': 1, 'synthetic': True,
                    'recorded_at': datetime.now(UTC).isoformat(),
                    'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                        'mongodb': mongo_version},
                    'source_sha256': {str(p.relative_to(ROOT)).replace(chr(92), '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                        [ROOT / 'scripts/engineering_smoke.py', frontend / 'e2e/full-stack/smoke.spec.ts', frontend / 'package-lock.json', ROOT / 'backend/requirements.txt']},
                    'passed': result == 0, 'seconds': round(time.monotonic() - started, 3),
                    'storage': 'real MongoDB, disposable database', 'backend_restarts': restarts,
                    'inference': 'offline deterministic; no live model'}, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    sys.exit(main())
