"""CLI: `python -m app serve`, `python -m app bootstrap`, `python -m app verify`, `python -m app seed-demo`."""
from __future__ import annotations
import os, sys

from .audit import Ledger
from .config import Settings
from .db import connect, init_db, tx
from . import security


def bootstrap(settings: Settings, email: str, password: str, name: str = "System Administrator"):
    import uuid
    from .audit import now
    from .tee import SimulatedTee
    tee = SimulatedTee(settings.secret)
    ledger = Ledger(settings.data_dir / "audit_checkpoints.jsonl", tee.release_key("ledger-checkpoint", tee.attest(), tee.measurement()), settings.checkpoint_every)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(settings.data_dir / "ps04.sqlite3")
    init_db(conn)
    with tx(conn):
        if conn.execute("SELECT 1 FROM users WHERE is_sysadmin=1").fetchone():
            return False
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        conn.execute("INSERT INTO users VALUES(?,?,?,?,1,'active',?)", (uid, email.lower(), name, security.hash_password(password, settings.pbkdf2_iterations), now()))
        ledger.append(conn, "user.bootstrap_sysadmin", actor=None, user_id=uid)
    return True


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "serve"
    settings = Settings.from_env()
    if cmd == "bootstrap":
        email, pw = os.environ.get("PS04_ADMIN_EMAIL"), os.environ.get("PS04_ADMIN_PASSWORD")
        if not email or not pw or len(pw) < 10:
            sys.exit("Set PS04_ADMIN_EMAIL and PS04_ADMIN_PASSWORD (>=10 chars)")
        print("created" if bootstrap(settings, email, pw) else "a system administrator already exists")
    elif cmd == "verify":
        from .tee import SimulatedTee
        tee = SimulatedTee(settings.secret)
        ledger = Ledger(settings.data_dir / "audit_checkpoints.jsonl", tee.release_key("ledger-checkpoint", tee.attest(), tee.measurement()))
        res = ledger.verify(connect(settings.data_dir / "ps04.sqlite3"))
        print(res)
        sys.exit(0 if res["ok"] else 1)
    elif cmd == "seed-demo":
        from .demo import seed
        seed(settings)
    else:
        import uvicorn
        from .main import create_app
        uvicorn.run(create_app(settings), host=os.environ.get("PS04_HOST", "127.0.0.1"), port=int(os.environ.get("PS04_PORT", "8000")))


if __name__ == "__main__":
    main(sys.argv)
