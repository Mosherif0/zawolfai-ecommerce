"""
Interactive setup: create the database and wire .env in one step.

Running it asks for the password you chose in the PostgreSQL installer, so
the value is never written to shell history or a log.

    python setup_postgres.py

It does three things:
  1. verifies the password against the running server
  2. creates DB_NAME if it does not exist
  3. writes the real password into .env
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ENV_PATH = BASE / ".env"

HOST = os.getenv("PGHOST", "localhost")
PORT = os.getenv("PGPORT", "5432")
USER = os.getenv("PGUSER", "postgres")
DB_NAME = os.getenv("PGDATABASE", "zawolf_ocr")


def ok(msg):
    print(f"  [ OK ] {msg}")


def fail(msg, hint=None):
    print(f"  [FAIL] {msg}")
    if hint:
        print(f"         {hint}")


def try_login(password: str):
    """Return (connected, message)."""
    import psycopg

    try:
        with psycopg.connect(host=HOST, port=PORT, user=USER,
                             dbname="postgres", password=password,
                             connect_timeout=5):
            return True, "authenticated"
    except psycopg.OperationalError as exc:
        first = str(exc).strip().splitlines()[0]
        return False, first
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def ensure_database(password: str):
    import psycopg

    with psycopg.connect(host=HOST, port=PORT, user=USER, dbname="postgres",
                         password=password, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
            if cur.fetchone():
                return False
            # CREATE DATABASE cannot run inside a transaction block
            conn.autocommit = True
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
            return True


def write_env(password: str):
    if ENV_PATH.is_file():
        text = ENV_PATH.read_text(encoding="utf-8")
    else:
        text = ""

    import re

    def set_key(key, value):
        nonlocal text
        pattern = rf"^{key}=.*$"
        if re.search(pattern, text, flags=re.M):
            text = re.sub(pattern, f"{key}={value}", text, flags=re.M)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += f"{key}={value}\n"

    set_key("DB_HOST", HOST)
    set_key("DB_PORT", PORT)
    set_key("DB_NAME", DB_NAME)
    set_key("DB_USER", USER)
    set_key("DB_PASSWORD", password)
    ENV_PATH.write_text(text, encoding="utf-8")


def main() -> int:
    print("=" * 64)
    print(" PostgreSQL setup")
    print("=" * 64)
    print(f"  server : {HOST}:{PORT}")
    print(f"  user   : {USER}")
    print(f"  database: {DB_NAME}")
    print()

    try:
        import psycopg
        ok(f"psycopg {psycopg.__version__}")
    except ImportError:
        fail("psycopg is not installed", 'fix: pip install "psycopg[binary]"')
        return 1

    password = getpass.getpass("  PostgreSQL password: ").strip()
    if not password:
        fail("empty password")
        return 1

    connected, message = try_login(password)
    if not connected:
        fail(f"could not log in: {message}")
        print("         the password is the one you typed in the installer")
        return 1
    ok("password accepted")

    try:
        created = ensure_database(password)
    except Exception as exc:
        fail(f"could not create the database: {exc}")
        return 1

    if created:
        ok(f"created database '{DB_NAME}'")
    else:
        ok(f"database '{DB_NAME}' already exists")

    try:
        write_env(password)
        ok(f"wrote {ENV_PATH.name}")
    except OSError as exc:
        fail(f"could not write {ENV_PATH.name}: {exc}")
        return 1

    print()
    print("=" * 64)
    print(" READY")
    print("   python migrate_sqlite_to_postgres.py --execute")
    print("   python app.py")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())