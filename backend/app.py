from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("IPL_DB_PATH", BASE_DIR / "ipl.db"))
SCHEMA_PATH = BASE_DIR / "schema.sqlite.sql"
SEED_PATH = BASE_DIR / "seed.sql"

CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "60"))
_cache: dict[str, tuple[float, Any]] = {}
ALLOWED_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}
MIN_IPL_SEASON = 2008
LAST_COMPLETED_SEASON = 2026
SCHEDULED_SEASON = 2027
MAX_AVAILABLE_SEASON = SCHEDULED_SEASON


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_cors_headers(response):
        configured_origin = os.environ.get("CORS_ORIGIN")
        allowed_origins = {configured_origin} if configured_origin else ALLOWED_ORIGINS
        request_origin = request.headers.get("Origin")
        if request_origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = request_origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/v1/seasons")
    def get_seasons():
        rows = query_all(
            """
            SELECT year, name, start_date, end_date
            FROM seasons
            ORDER BY year DESC
            """
        )
        return jsonify(
            {
                "data": [
                    {
                        "year": row["year"],
                        "name": row["name"],
                        "startDate": row["start_date"],
                        "endDate": row["end_date"],
                    }
                    for row in rows
                ]
            }
        )

    @app.get("/v1/seasons/<int:season_year>/matches")
    def get_matches(season_year: int):
        validation_error = validate_season_year(season_year)
        if validation_error:
            return validation_error

        page = parse_int_arg("page", 1)
        page_size = parse_int_arg("pageSize", 20)
        status = request.args.get("status")
        team_code = request.args.get("teamCode")

        if page < 1:
            return error_response("bad_request", "page must be at least 1", 400)
        if page_size < 1 or page_size > 100:
            return error_response("bad_request", "pageSize must be between 1 and 100", 400)
        if status and status not in {"upcoming", "live", "completed"}:
            return error_response(
                "bad_request", "status must be upcoming, live, or completed", 400
            )
        if team_code and not team_code.isalnum():
            return error_response("bad_request", "teamCode must be alphanumeric", 400)

        season = get_season(season_year)
        if not season:
            return error_response("not_found", f"Season {season_year} was not found", 404)

        filters = ["m.season_id = ?"]
        params: list[Any] = [season["id"]]

        if status:
            filters.append("m.status = ?")
            params.append(status)
        if team_code:
            filters.append("(home.code = ? OR away.code = ?)")
            params.extend([team_code.upper(), team_code.upper()])

        where_clause = " AND ".join(filters)
        total = query_one(
            f"""
            SELECT COUNT(*) AS total
            FROM matches m
            JOIN teams home ON home.id = m.home_team_id
            JOIN teams away ON away.id = m.away_team_id
            WHERE {where_clause}
            """,
            params,
        )["total"]

        rows = query_all(
            f"""
            SELECT
                m.id,
                m.match_number,
                m.match_date,
                m.status,
                m.result_type,
                m.result_summary,
                v.name AS venue_name,
                v.city AS venue_city,
                home.id AS home_id,
                home.code AS home_code,
                home.name AS home_name,
                away.id AS away_id,
                away.code AS away_code,
                away.name AS away_name,
                winner.code AS winner_code,
                winner.name AS winner_name
            FROM matches m
            JOIN venues v ON v.id = m.venue_id
            JOIN teams home ON home.id = m.home_team_id
            JOIN teams away ON away.id = m.away_team_id
            LEFT JOIN teams winner ON winner.id = m.winner_team_id
            WHERE {where_clause}
            ORDER BY m.match_date DESC, m.match_number DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, (page - 1) * page_size],
        )

        scores = get_scores_for_matches([row["id"] for row in rows])

        return jsonify(
            {
                "data": [match_summary(row, scores.get(row["id"], {})) for row in rows],
                "pagination": {
                    "page": page,
                    "pageSize": page_size,
                    "totalItems": total,
                    "totalPages": (total + page_size - 1) // page_size,
                },
            }
        )

    @app.get("/v1/seasons/<int:season_year>/matches/<int:match_number>")
    def get_match(season_year: int, match_number: int):
        validation_error = validate_season_year(season_year)
        if validation_error:
            return validation_error

        row = query_one(
            """
            SELECT
                m.id,
                m.match_number,
                m.match_date,
                m.status,
                m.result_type,
                m.result_summary,
                v.name AS venue_name,
                v.city AS venue_city,
                home.code AS home_code,
                home.name AS home_name,
                away.code AS away_code,
                away.name AS away_name,
                winner.code AS winner_code,
                winner.name AS winner_name
            FROM matches m
            JOIN seasons s ON s.id = m.season_id
            JOIN venues v ON v.id = m.venue_id
            JOIN teams home ON home.id = m.home_team_id
            JOIN teams away ON away.id = m.away_team_id
            LEFT JOIN teams winner ON winner.id = m.winner_team_id
            WHERE s.year = ? AND m.match_number = ?
            """,
            [season_year, match_number],
        )
        if not row:
            return error_response(
                "not_found",
                f"Match {match_number} was not found in season {season_year}",
                404,
            )

        innings = query_all(
            """
            SELECT
                i.innings_number,
                batting.code AS batting_code,
                batting.name AS batting_name,
                bowling.code AS bowling_code,
                bowling.name AS bowling_name,
                i.runs,
                i.wickets,
                i.balls_faced,
                i.extras
            FROM innings_scores i
            JOIN teams batting ON batting.id = i.batting_team_id
            JOIN teams bowling ON bowling.id = i.bowling_team_id
            WHERE i.match_id = ?
            ORDER BY i.innings_number ASC
            """,
            [row["id"]],
        )

        return jsonify(
            {
                "data": {
                    "matchNumber": row["match_number"],
                    "matchDate": row["match_date"],
                    "venue": {"name": row["venue_name"], "city": row["venue_city"]},
                    "homeTeam": {"code": row["home_code"], "name": row["home_name"]},
                    "awayTeam": {"code": row["away_code"], "name": row["away_name"]},
                    "status": row["status"],
                    "winner": match_winner_ref(
                        row["winner_code"], row["winner_name"], row["status"]
                    ),
                    "resultType": row["result_type"],
                    "resultSummary": row["result_summary"],
                    "innings": [
                        {
                            "inningsNumber": item["innings_number"],
                            "battingTeam": {
                                "code": item["batting_code"],
                                "name": item["batting_name"],
                            },
                            "bowlingTeam": {
                                "code": item["bowling_code"],
                                "name": item["bowling_name"],
                            },
                            "runs": item["runs"],
                            "wickets": item["wickets"],
                            "ballsFaced": item["balls_faced"],
                            "overs": balls_to_overs(item["balls_faced"]),
                            "extras": item["extras"],
                        }
                        for item in innings
                    ],
                }
            }
        )

    @app.get("/v1/seasons/<int:season_year>/points-table")
    def get_points_table(season_year: int):
        validation_error = validate_season_year(season_year)
        if validation_error:
            return validation_error

        cache_key = f"points-table:{season_year}"
        cached = cache_get(cache_key)
        if cached:
            return jsonify(cached)

        rows = query_all(
            """
            SELECT
                ts.rank,
                ts.matches_played,
                ts.won,
                ts.lost,
                ts.no_result,
                ts.points,
                ts.net_run_rate,
                ts.last_calculated_at,
                t.code,
                t.name,
                t.logo_url
            FROM team_standings ts
            JOIN seasons s ON s.id = ts.season_id
            JOIN teams t ON t.id = ts.team_id
            WHERE s.year = ?
            ORDER BY ts.rank ASC
            """,
            [season_year],
        )
        if not rows and not get_season(season_year):
            return error_response("not_found", f"Season {season_year} was not found", 404)

        payload = {
            "data": [
                {
                    "rank": row["rank"],
                    "team": {
                        "code": row["code"],
                        "name": row["name"],
                        "logoUrl": row["logo_url"],
                    },
                    "played": row["matches_played"],
                    "won": row["won"],
                    "lost": row["lost"],
                    "noResult": row["no_result"],
                    "points": row["points"],
                    "netRunRate": float(row["net_run_rate"]),
                }
                for row in rows
            ],
            "meta": {
                "season": season_year,
                "lastCalculatedAt": rows[0]["last_calculated_at"] if rows else None,
                "cacheTtlSeconds": CACHE_TTL_SECONDS,
            },
        }
        cache_set(cache_key, payload)
        return jsonify(payload)

    @app.get("/v1/seasons/<int:season_year>/teams")
    def get_teams(season_year: int):
        cached = cache_get(f"teams:{season_year}")
        if cached:
            return jsonify(cached)

        rows = query_all(
            """
            SELECT
                t.code,
                t.name,
                t.home_city,
                t.logo_url,
                p.id AS captain_id,
                p.full_name AS captain_name
            FROM team_seasons tse
            JOIN seasons s ON s.id = tse.season_id
            JOIN teams t ON t.id = tse.team_id
            LEFT JOIN players p ON p.id = tse.captain_player_id
            WHERE s.year = ?
            ORDER BY t.name ASC
            """,
            [season_year],
        )
        if not rows and not get_season(season_year):
            return error_response("not_found", f"Season {season_year} was not found", 404)

        payload = {
            "data": [
                {
                    "code": row["code"],
                    "name": row["name"],
                    "homeCity": row["home_city"],
                    "captain": player_ref(row["captain_id"], row["captain_name"]),
                    "logoUrl": row["logo_url"],
                }
                for row in rows
            ]
        }
        cache_set(f"teams:{season_year}", payload)
        return jsonify(payload)

    @app.get("/v1/seasons/<int:season_year>/teams/<team_code>")
    def get_team(season_year: int, team_code: str):
        team_code = team_code.upper()
        if not team_code.isalnum():
            return error_response("bad_request", "teamCode must be alphanumeric", 400)

        cache_key = f"team:{season_year}:{team_code}"
        cached = cache_get(cache_key)
        if cached:
            return jsonify(cached)

        team = query_one(
            """
            SELECT
                tse.id AS team_season_id,
                t.code,
                t.name,
                t.home_city,
                t.logo_url,
                p.id AS captain_id,
                p.full_name AS captain_name
            FROM team_seasons tse
            JOIN seasons s ON s.id = tse.season_id
            JOIN teams t ON t.id = tse.team_id
            LEFT JOIN players p ON p.id = tse.captain_player_id
            WHERE s.year = ? AND t.code = ?
            """,
            [season_year, team_code],
        )
        if not team:
            return error_response(
                "not_found",
                f"Team {team_code} was not found in season {season_year}",
                404,
            )

        squad = query_all(
            """
            SELECT
                p.id,
                p.full_name,
                p.country,
                sm.player_role,
                sm.is_overseas
            FROM squad_members sm
            JOIN players p ON p.id = sm.player_id
            WHERE sm.team_season_id = ?
            ORDER BY
                CASE sm.player_role
                    WHEN 'batter' THEN 1
                    WHEN 'WK' THEN 2
                    WHEN 'all-rounder' THEN 3
                    ELSE 4
                END,
                p.full_name ASC
            """,
            [team["team_season_id"]],
        )

        payload = {
            "data": {
                "code": team["code"],
                "name": team["name"],
                "homeCity": team["home_city"],
                "captain": player_ref(team["captain_id"], team["captain_name"]),
                "logoUrl": team["logo_url"],
                "squad": [
                    {
                        "id": player["id"],
                        "name": player["full_name"],
                        "country": player["country"],
                        "role": player["player_role"],
                        "isOverseas": bool(player["is_overseas"]),
                    }
                    for player in squad
                ],
            }
        }
        cache_set(cache_key, payload)
        return jsonify(payload)

    return app


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        count = conn.execute("SELECT COUNT(*) FROM seasons").fetchone()[0]
        if count == 0:
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
        backfill_historical_demo_seasons(conn)
        refresh_all_standings(conn)
        conn.commit()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_one(sql: str, params: list[Any] | tuple[Any, ...] = ()) -> sqlite3.Row | None:
    with closing(get_conn()) as conn:
        return conn.execute(sql, params).fetchone()


def query_all(sql: str, params: list[Any] | tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with closing(get_conn()) as conn:
        return conn.execute(sql, params).fetchall()


def get_season(season_year: int) -> sqlite3.Row | None:
    return query_one("SELECT id, year FROM seasons WHERE year = ?", [season_year])


def parse_int_arg(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return -1


def validate_season_year(season_year: int):
    if season_year < MIN_IPL_SEASON:
        return error_response(
            "ipl_not_started",
            f"IPL did not exist before {MIN_IPL_SEASON}",
            400,
        )
    if season_year > MAX_AVAILABLE_SEASON:
        return error_response(
            "season_not_available",
            f"IPL season {season_year} is upcoming or not available yet",
            422,
        )
    return None


def get_scores_for_matches(match_ids: list[int]) -> dict[int, dict[int, sqlite3.Row]]:
    if not match_ids:
        return {}
    placeholders = ",".join(["?"] * len(match_ids))
    rows = query_all(
        f"""
        SELECT *
        FROM innings_scores
        WHERE match_id IN ({placeholders})
        ORDER BY innings_number ASC
        """,
        match_ids,
    )
    grouped: dict[int, dict[int, sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["match_id"], {})[row["batting_team_id"]] = row
    return grouped


def match_summary(row: sqlite3.Row, scores_by_team: dict[int, sqlite3.Row]) -> dict[str, Any]:
    home_score = scores_by_team.get(row["home_id"])
    away_score = scores_by_team.get(row["away_id"])
    return {
        "matchNumber": row["match_number"],
        "matchDate": row["match_date"],
        "venue": {"name": row["venue_name"], "city": row["venue_city"]},
        "teams": {
            "home": {
                "code": row["home_code"],
                "name": row["home_name"],
                "score": score_payload(home_score),
            },
            "away": {
                "code": row["away_code"],
                "name": row["away_name"],
                "score": score_payload(away_score),
            },
        },
        "winner": match_winner_ref(row["winner_code"], row["winner_name"], row["status"]),
        "status": row["status"],
        "resultType": row["result_type"],
        "resultSummary": row["result_summary"],
    }


def score_payload(score: sqlite3.Row | None) -> dict[str, Any] | None:
    if score is None:
        return None
    return {
        "runs": score["runs"],
        "wickets": score["wickets"],
        "overs": balls_to_overs(score["balls_faced"]),
    }


def balls_to_overs(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def team_ref(code: str | None, name: str | None) -> dict[str, str] | None:
    if not code or not name:
        return None
    return {"code": code, "name": name}


def match_winner_ref(code: str | None, name: str | None, status: str) -> dict[str, str]:
    if code and name:
        return {"code": code, "name": name}
    if status in {"upcoming", "live"}:
        return {"code": "TBD", "name": "TBD"}
    return {"code": "NONE", "name": "No result"}


def player_ref(player_id: int | None, name: str | None) -> dict[str, Any] | None:
    if not player_id or not name:
        return None
    return {"id": player_id, "name": name}


def backfill_historical_demo_seasons(conn: sqlite3.Connection) -> None:
    team_ids = [row[0] for row in conn.execute("SELECT id FROM teams ORDER BY id LIMIT 10")]
    player_ids = [row[0] for row in conn.execute("SELECT id FROM players ORDER BY id")]
    if len(team_ids) < 2 or len(player_ids) < 4:
        return

    team_names = {
        row[0]: row[1]
        for row in conn.execute("SELECT id, name FROM teams")
    }

    captain_rows = conn.execute(
        """
        SELECT team_id, MIN(captain_player_id)
        FROM team_seasons
        WHERE captain_player_id IS NOT NULL
        GROUP BY team_id
        """
    ).fetchall()
    captain_by_team = {team_id: captain_id for team_id, captain_id in captain_rows}
    roles = ["batter", "WK", "all-rounder", "bowler"]

    for year in range(MIN_IPL_SEASON, SCHEDULED_SEASON + 1):
        conn.execute(
            """
            INSERT OR IGNORE INTO seasons (year, name, start_date, end_date)
            VALUES (?, ?, ?, ?)
            """,
            (
                year,
                f"Indian Premier League {year}",
                f"{year}-03-20",
                f"{year}-05-31",
            ),
        )
        season_id = conn.execute("SELECT id FROM seasons WHERE year = ?", (year,)).fetchone()[0]

        for team_id in team_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO team_seasons (season_id, team_id, captain_player_id)
                VALUES (?, ?, ?)
                """,
                (season_id, team_id, captain_by_team.get(team_id)),
            )
            team_season_id = conn.execute(
                "SELECT id FROM team_seasons WHERE season_id = ? AND team_id = ?",
                (season_id, team_id),
            ).fetchone()[0]
            squad_count = conn.execute(
                "SELECT COUNT(*) FROM squad_members WHERE team_season_id = ?",
                (team_season_id,),
            ).fetchone()[0]
            if squad_count == 0:
                for offset, role in enumerate(roles):
                    player_id = player_ids[(team_id * 3 + year + offset) % len(player_ids)]
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO squad_members
                            (team_season_id, player_id, player_role, is_overseas)
                        VALUES (?, ?, ?, ?)
                        """,
                        (team_season_id, player_id, role, 1 if offset == 3 else 0),
                    )

        existing_matches = conn.execute(
            "SELECT COUNT(*) FROM matches WHERE season_id = ?",
            (season_id,),
        ).fetchone()[0]
        if existing_matches == 74:
            continue

        conn.execute(
            """
            DELETE FROM innings_scores
            WHERE match_id IN (SELECT id FROM matches WHERE season_id = ?)
            """,
            (season_id,),
        )
        conn.execute("DELETE FROM matches WHERE season_id = ?", (season_id,))
        conn.execute("DELETE FROM team_standings WHERE season_id = ?", (season_id,))

        for match_number in range(1, 75):
            home_team_id = team_ids[(match_number + year) % len(team_ids)]
            away_team_id = team_ids[(match_number + year + 4) % len(team_ids)]
            if home_team_id == away_team_id:
                away_team_id = team_ids[(match_number + year + 5) % len(team_ids)]

            venue_id = ((match_number + year) % 10) + 1
            home_runs = 145 + ((year + match_number * 7) % 62)
            away_runs = 138 + ((year + match_number * 5) % 58)
            is_scheduled = year == SCHEDULED_SEASON
            winner_team_id = None if is_scheduled else home_team_id if home_runs >= away_runs else away_team_id
            match_date = date(year, 3, 20) + timedelta(days=match_number - 1)
            winner_name = team_names.get(winner_team_id, "TBD")

            conn.execute(
                """
                INSERT INTO matches (
                    season_id, match_number, match_date, venue_id, home_team_id, away_team_id,
                    toss_winner_team_id, winner_team_id, status, result_type, result_summary,
                    started_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    season_id,
                    match_number,
                    f"{match_date.isoformat()}T14:00:00Z",
                    venue_id,
                    home_team_id,
                    away_team_id,
                    home_team_id,
                    winner_team_id,
                    "upcoming" if is_scheduled else "completed",
                    "normal",
                    None if is_scheduled else f"{winner_name} won in demo result",
                    None if is_scheduled else f"{match_date.isoformat()}T14:00:00Z",
                    None if is_scheduled else f"{match_date.isoformat()}T18:00:00Z",
                ),
            )
            match_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            if is_scheduled:
                continue

            conn.execute(
                """
                INSERT INTO innings_scores
                    (match_id, innings_number, batting_team_id, bowling_team_id, runs, wickets, balls_faced, extras)
                VALUES (?, 1, ?, ?, ?, ?, 120, 6)
                """,
                (match_id, home_team_id, away_team_id, home_runs, 3 + ((year + match_number) % 6)),
            )
            conn.execute(
                """
                INSERT INTO innings_scores
                    (match_id, innings_number, batting_team_id, bowling_team_id, runs, wickets, balls_faced, extras)
                VALUES (?, 2, ?, ?, ?, ?, 120, 5)
                """,
                (match_id, away_team_id, home_team_id, away_runs, 4 + ((year + match_number) % 5)),
            )


def refresh_all_standings(conn: sqlite3.Connection) -> None:
    season_ids = [row[0] for row in conn.execute("SELECT id FROM seasons")]
    for season_id in season_ids:
        refresh_standings_for_season(conn, season_id)


def refresh_standings_for_season(conn: sqlite3.Connection, season_id: int) -> None:
    team_ids = [
        row[0]
        for row in conn.execute(
            "SELECT team_id FROM team_seasons WHERE season_id = ?",
            (season_id,),
        )
    ]
    if not team_ids:
        return

    stats = {
        team_id: {
            "team_name": conn.execute(
                "SELECT name FROM teams WHERE id = ?",
                (team_id,),
            ).fetchone()[0],
            "played": 0,
            "won": 0,
            "lost": 0,
            "nr": 0,
            "points": 0,
            "runs_for": 0,
            "balls_for": 0,
            "runs_against": 0,
            "balls_against": 0,
        }
        for team_id in team_ids
    }

    matches = conn.execute(
        """
        SELECT id, home_team_id, away_team_id, winner_team_id, result_type
        FROM matches
        WHERE season_id = ? AND status = 'completed'
        """,
        (season_id,),
    ).fetchall()

    for match_id, home_team_id, away_team_id, winner_team_id, result_type in matches:
        if home_team_id not in stats or away_team_id not in stats:
            continue

        stats[home_team_id]["played"] += 1
        stats[away_team_id]["played"] += 1

        if result_type in {"no_result", "abandoned", "tie"} or winner_team_id is None:
            stats[home_team_id]["nr"] += 1
            stats[away_team_id]["nr"] += 1
            stats[home_team_id]["points"] += 1
            stats[away_team_id]["points"] += 1
        else:
            loser_team_id = away_team_id if winner_team_id == home_team_id else home_team_id
            stats[winner_team_id]["won"] += 1
            stats[winner_team_id]["points"] += 2
            stats[loser_team_id]["lost"] += 1

        innings = conn.execute(
            """
            SELECT batting_team_id, bowling_team_id, runs, balls_faced
            FROM innings_scores
            WHERE match_id = ?
            """,
            (match_id,),
        ).fetchall()
        for batting_team_id, bowling_team_id, runs, balls_faced in innings:
            if batting_team_id in stats:
                stats[batting_team_id]["runs_for"] += runs
                stats[batting_team_id]["balls_for"] += balls_faced
            if bowling_team_id in stats:
                stats[bowling_team_id]["runs_against"] += runs
                stats[bowling_team_id]["balls_against"] += balls_faced

    ranked_rows = []
    for team_id, row in stats.items():
        run_rate_for = (
            row["runs_for"] / (row["balls_for"] / 6)
            if row["balls_for"]
            else 0
        )
        run_rate_against = (
            row["runs_against"] / (row["balls_against"] / 6)
            if row["balls_against"]
            else 0
        )
        row["nrr"] = round(run_rate_for - run_rate_against, 3)
        ranked_rows.append((team_id, row))

    ranked_rows.sort(
        key=lambda item: (
            -item[1]["points"],
            -item[1]["nrr"],
            -item[1]["won"],
            item[1]["team_name"],
        ),
    )

    conn.execute("DELETE FROM team_standings WHERE season_id = ?", (season_id,))
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for rank, (team_id, row) in enumerate(ranked_rows, start=1):
        conn.execute(
            """
            INSERT INTO team_standings (
                season_id, team_id, rank, matches_played, won, lost, no_result,
                points, net_run_rate, last_calculated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                season_id,
                team_id,
                rank,
                row["played"],
                row["won"],
                row["lost"],
                row["nr"],
                row["points"],
                row["nrr"],
                now,
            ),
        )


def cache_get(key: str) -> Any | None:
    value = _cache.get(key)
    if not value:
        return None
    expires_at, payload = value
    if expires_at < time.time():
        _cache.pop(key, None)
        return None
    return payload


def cache_set(key: str, payload: Any) -> None:
    _cache[key] = (time.time() + CACHE_TTL_SECONDS, payload)


def error_response(code: str, message: str, status_code: int):
    return jsonify({"error": {"code": code, "message": message, "details": {}}}), status_code


init_db()
app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
