"""
Setup doctor.

One command that answers "why is it not working?" instead of a
connection-refused message with no explanation. Checks, in order:

  1. psycopg installed
  2. .env present and complete
  3. something listening on the Postgres port
  4. the credentials actually authenticate
  5. the database exists

Exit code 0 = ready, 1 = something needs fixing (the report says what).
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"
EXAMPLE = Path(__file__).resolve().parent / ".env.example"

REQUIRED = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")


def ok(msg: str) -> None:
    print(f"  [ OK ] {msg}")


def bad(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def check_driver() -> bool:
    print("\n1. PostgreSQL driver")
    try:
        import psycopg  # noqa: F401

        ok(f"psycopg {psycopg.__version__} installed")
        return True
    except ImportError:
        bad("psycopg is not installed")
        print("         fix: pip install \"psycopg[binary]\"")
        return False


def load_env() -> dict:
    print("\n2. Configuration (.env)")
    if not ENV_PATH.is_file():
        bad(f"{ENV_PATH.name} not found")
        if EXAMPLE.is_file():
            print(f"         fix: copy {EXAMPLE.name} to .env, then edit it")
        return {}
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH, override=True)
    except ImportError:
        pass

    values = {k: os.getenv(k) for k in REQUIRED}
    missing = [k for k, v in values.items() if not v]
    if missing:
        bad(f"missing in .env: {', '.join(missing)}")
        print(f"         fix: add them to {ENV_PATH.name}")
    else:
        ok("all required keys present")
    return values


def check_port(host: str, port: str) -> bool:
    print(f"\n3. Is something listening on {host}:{port}?")
    try:
        port_num = int(port or 5432)
    except ValueError:
        bad(f"DB_PORT is not a number: {port!r}")
        return False

    try:
        with socket.create_connection((host, port_num), timeout=4):
            ok(f"something accepted a connection on port {port_num}")
            return True
    except socket.timeout:
        bad(f"port {port_num} exists but did not answer in time")
        return False
    except OSError as exc:
        bad(f"nothing is listening on port {port_num} ({exc.strerror})")
        print("         fix: start the Postgres service, or check DB_PORT")
        print("               Start Menu -> type 'postgres' -> 'SQL Shell (psql)'")
        print("               or: services.msc -> 'postgresql-x64-16' -> Start")
        return False


def check_login(cfg: dict) -> bool:
    print("\n4. Can we log in?")
    try:
        import psycopg
    except ImportError:
        bad("skipped (psycopg missing)")
        return False

    host, port = cfg.get("DB_HOST"), cfg.get("DB_PORT") or 5432
    user, password = cfg.get("DB_USER"), cfg.get("DB_PASSWORD")

    # Step A: the default database, so a missing app database is reported
    # separately from a bad password.
    for dbname, label in ((cfg.get("DB_NAME"), "application database"),
                          ("postgres", "server (postgres db)")):
        try:
            with psycopg.connect(host=host, port=port, dbname=dbname,
                                 user=user, password=password, connect_timeout=5):
                ok(f"authenticated to {dbname!r} ({label})")
                return True
        except psycopg.OperationalError as exc:
            message = str(exc).strip().splitlines()[0]
            if "password authentication failed" in message:
                bad("password rejected")
                print("         fix: DB_PASSWORD does not match the installer password")
                return False
            if "does not exist" in message:
                warn(f"database {dbname!r} does not exist yet")
                print(f"         fix: in SQL Shell run: CREATE DATABASE {dbname};")
                return False
            bad(f"cannot reach {dbname!r}: {message}")
            return False
        except Exception as exc:
            bad(f"unexpected error: {type(exc).__name__}: {exc}")
            return False
    return False


def check_tables() -> bool:
    print("\n5. Warehouse tables")
    try:
        import schema as schema_mod
        import warehouse as wh
    except ImportError as exc:
        bad(f"cannot import the project modules: {exc}")
        return False

    if not wh.using_postgres():
        warn("DB_HOST is not set, so this will use SQLite")
        return True

    try:
        with wh.connection() as conn:
            counts = schema_mod.table_counts(conn, "postgres")
    except Exception as exc:
        bad(f"cannot apply/read the schema: {type(exc).__name__}: {exc}")
        return False

    empty = [t for t, n in counts.items() if n == 0]
    ok(f"tables present: {', '.join(f'{t}={n}' for t, n in counts.items())}")
    if empty:
        warn(f"still empty: {', '.join(empty)}")
        print("         fix (if you expected data):")
        print("               python migrate_sqlite_to_postgres.py --execute")
    return True


def main() -> int:
    print("=" * 62)
    print(" ZAWOLF OCR - setup doctor")
    print("=" * 62)

    driver = check_driver()
    cfg = load_env()

    if not driver or not all(cfg.get(k) for k in REQUIRED):
        print("\n" + "=" * 62)
        print(" NOT READY - fix the [FAIL] lines above, then run this again.")
        print("=" * 62)
        return 1

    reachable = check_port(cfg["DB_HOST"], cfg["DB_PORT"])
    login = check_login(cfg) if reachable else False
    check_tables()

    ready = driver and reachable and login
    print("\n" + "=" * 62)
    if ready:
        print(" READY - you can run:  python app.py")
    else:
        print(" NOT READY - fix the [FAIL] lines above, then run this again.")
    print("=" * 62)
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())