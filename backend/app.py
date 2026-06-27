from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("IPL_DB_PATH", BASE_DIR / "ipl.db"))
SCHEMA_PATH = BASE_DIR / "schema.sqlite.sql"
SEED_PATH = BASE_DIR / "seed.sql"

CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "60"))
_cache: dict[str, tuple[float, Any]] = {}


def create_app() -> Flask:
    app = Flask(__name__)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = os.environ.get(
            "CORS_ORIGIN", "http://localhost:5173"
        )
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
                    "winner": team_ref(row["winner_code"], row["winner_name"]),
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
    if season_year < 2008 or season_year > 2100:
        return error_response("bad_request", "seasonYear is outside the IPL range", 400)
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
        "winner": team_ref(row["winner_code"], row["winner_name"]),
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


def player_ref(player_id: int | None, name: str | None) -> dict[str, Any] | None:
    if not player_id or not name:
        return None
    return {"id": player_id, "name": name}


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
