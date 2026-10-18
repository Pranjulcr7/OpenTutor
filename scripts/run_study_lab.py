"""Run the local API and web UI together; optionally perform an HTTP smoke test."""

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=3001)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if not shutil.which("npm") or not (ROOT / "apps/web/node_modules/next").exists():
        parser.error("Install Node.js and run npm ci --prefix apps/web first.")
    for port in [args.api_port, args.web_port]:
        with socket.socket() as check:
            try:
                check.bind(("127.0.0.1", port))
            except OSError:
                parser.error(
                    f"Port {port} is occupied; stop the old server or choose another port."
                )
    load_dotenv(ROOT / ".env")
    env = {**os.environ, "NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{args.api_port}/api"}
    children = []
    try:
        children.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                ],
                cwd=ROOT / "apps/api",
                env=env,
                start_new_session=True,
            )
        )
        children.append(
            subprocess.Popen(
                [
                    "npm",
                    "run",
                    "dev",
                    "--",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(args.web_port),
                ],
                cwd=ROOT / "apps/web",
                env=env,
                start_new_session=True,
            )
        )
        print(f"Study Lab: http://127.0.0.1:{args.web_port}/study-lab", flush=True)
        if args.smoke_test:
            import httpx

            urls = [
                f"http://127.0.0.1:{args.api_port}/openapi.json",
                *[
                    f"http://127.0.0.1:{args.web_port}/{path}"
                    for path in ["study-lab", "experiments", "api/health"]
                ],
            ]
            with httpx.Client(trust_env=False, timeout=15) as client:
                for url in urls:
                    deadline = time.monotonic() + 120
                    while time.monotonic() < deadline:
                        if any(child.poll() is not None for child in children):
                            raise RuntimeError("A server exited during startup.")
                        try:
                            response = client.get(url)
                            if response.status_code == 200:
                                print(f"PASS 200 {url}", flush=True)
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.5)
                    else:
                        raise RuntimeError(f"Startup check failed: {url}")
            return 0
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
