"""Backfill `tier` column for existing users."""
import sqlite3
from typing import Iterator

BATCH_SIZE = 500


def get_unbackfilled_ids(conn: sqlite3.Connection) -> Iterator[list[int]]:
    """Yield batches of user IDs that lack a tier value."""
    cur = conn.execute("SELECT MAX(id) FROM users")
    max_id = cur.fetchone()[0]

    for start in range(0, max_id, BATCH_SIZE):
        end = start + BATCH_SIZE
        cur = conn.execute(
            "SELECT id FROM users WHERE id >= ? AND id < ? AND tier IS NULL",
            (start, end),
        )
        ids = [row[0] for row in cur.fetchall()]
        if ids:
            yield ids


def backfill_tier(conn: sqlite3.Connection, user_id: int) -> None:
    """Set tier='free' for the given user."""
    conn.execute(
        "UPDATE users SET tier = 'free' WHERE id = ?",
        (user_id,),
    )


def run_migration(db_path: str) -> int:
    """Run the migration. Returns the number of rows backfilled."""
    conn = sqlite3.connect(db_path)
    try:
        total = 0
        for batch in get_unbackfilled_ids(conn):
            for uid in batch:
                backfill_tier(conn, uid)
                total += 1
        return total
    finally:
        conn.close()
