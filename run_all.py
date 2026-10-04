"""
Run the Zawolf backend services together.

Each service stays independently runnable (its own `python -m uvicorn ...`),
because that is how you debug one of them. This launcher is for the other
case: bringing the whole backend up with one command and seeing, at a glance,
which piece came up and which did not.

    python run_all.py                 # start everything
    python run_all.py --check         # verify configuration and exit
    python run_all.py --only ocr      # start a subset

Ports are fixed and non-overlapping:

    recommendations  8100   catalog, BM25 search, related items
    ocr              8200   receipt upload, validation, warehouse
    chatbot          8300   conversational assistant
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import zawolf_config as config  # noqa: E402


def health_url(port: int, path: str = "/health") -> str:
    return f"http://127.0.0.1:{port}{path}"


def probe(url: str, timeout: float = 2.0) -> Optional[int]:
    """Return the status code, or None when the service is not answering."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def wait_for(port: int, path: str, attempts: int = 25, delay: float = 0.8) -> Optional[int]:
    for _ in range(attempts):
        status = probe(health_url(port, path))
        if status is not None:
            return status
        time.sleep(delay)
    return None


def start(name: str, directory: Path, target: str, port: int,
          path: str = "/health") -> Optional[subprocess.Popen]:
    command = [
        sys.executable, "-m", "uvicorn", target,
        "--host", "127.0.0.1", "--port", str(port),
    ]
    try:
        process = subprocess.Popen(
            command, cwd=str(directory),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        print(f"  [FAIL] {name}: could not start ({exc})")
        return None

    status = wait_for(port, path)
    if status is None:
        print(f"  [FAIL] {name}: started but {health_url(port, path)} never answered")
        process.terminate()
        return None

    print(f"  [ OK ] {name:16} http://127.0.0.1:{port}{path}  (HTTP {status})")
    return process


def run_check() -> int:
    print("=" * 66)
    print(" ZAWOLF BACKEND - configuration check")
    print("=" * 66)

    snapshot = config.describe()
    print(f"\nworkspace: {snapshot['workspace']}")
    print(f"warehouse: {snapshot['warehouse']['backend']} "
          f"({snapshot['warehouse']['database']})")
    print(f"ocr lang : {snapshot['ocr']['language']}")

    print("\ndata files")
    for key in ("catalog_csv", "catalog_images", "transactions_csv", "inventory_csv"):
        entry = snapshot[key]
        mark = "OK  " if entry["exists"] else "MISS"
        print(f"  [{mark}] {key:18} {entry['path']}")

    print("\nservices")
    for name, entry in snapshot["services"].items():
        directory = Path(entry["dir"])
        mark = "OK  " if directory.is_dir() else "MISS"
        print(f"  [{mark}] {name:16} port {entry['port']:>5}  {entry['target']}")

    problems = config.validate()
    print()
    if problems:
        print("PROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("configuration OK")
    return 0


def run_services(only: Optional[List[str]]) -> int:
    print("=" * 66)
    print(" ZAWOLF BACKEND")
    print("=" * 66)

    processes = []
    for name, (directory, target, port) in config.SERVICES.items():
        if only and name not in only:
            continue
        if not Path(directory).is_dir():
            print(f"  [SKIP] {name}: {directory} does not exist")
            continue

        # All three services expose /health with the same shape.
        process = start(name, Path(directory), target, port)
        if process:
            processes.append((name, process))

    if not processes:
        print("\nnothing started")
        return 1

    print()
    print("Ctrl+C to stop everything.")
    for name, (_, _, port) in config.SERVICES.items():
        print(f"  {name:16} http://127.0.0.1:{port}")

    try:
        while True:
            time.sleep(1)
            for name, process in processes:
                if process.poll() is not None:
                    print(f"  [WARN] {name} exited with code {process.returncode}")
            if all(p.poll() is not None for _, p in processes):
                break
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("stopped")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Zawolf backend services")
    parser.add_argument("--check", action="store_true",
                        help="verify configuration and exit")
    parser.add_argument("--only", nargs="*",
                        choices=list(config.SERVICES),
                        help="start only these services")
    args = parser.parse_args()

    if args.check:
        return run_check()
    return run_services(args.only)


if __name__ == "__main__":
    raise SystemExit(main())