import sqlite3
from pathlib import Path

def test_db_exists_and_has_table():
    db = Path("data/catalog.db")
    assert db.exists(), "Run `make all` first to generate the SQLite DB."

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recordings';")
    assert cur.fetchone() is not None
    conn.close()
