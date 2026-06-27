from __future__ import annotations

import sqlite3
import time
from contextlib import closing

from app import DB_PATH, refresh_all_standings


def main() -> None:
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with closing(sqlite3.connect(DB_PATH)) as conn:
        run_id = conn.execute(
            """
            INSERT INTO standings_refresh_runs (started_at, status, message)
            VALUES (?, 'running', ?)
            """,
            (started_at, "Scheduled standings refresh started"),
        ).lastrowid
        try:
            refresh_all_standings(conn)
            matches_scanned = conn.execute(
                "SELECT COUNT(*) FROM matches WHERE status = 'completed'"
            ).fetchone()[0]
            conn.execute(
                """
                UPDATE standings_refresh_runs
                SET completed_at = ?, status = 'succeeded', matches_scanned = ?, message = ?
                WHERE id = ?
                """,
                (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    matches_scanned,
                    "Standings refreshed from completed matches",
                    run_id,
                ),
            )
            conn.commit()
        except Exception as exc:
            conn.execute(
                """
                UPDATE standings_refresh_runs
                SET completed_at = ?, status = 'failed', message = ?
                WHERE id = ?
                """,
                (
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    str(exc),
                    run_id,
                ),
            )
            conn.commit()
            raise


if __name__ == "__main__":
    main()
