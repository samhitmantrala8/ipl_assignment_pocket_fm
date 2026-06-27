# IPL Platform API + Frontend

This repo implements the IPL Platform problem statement with a Flask backend, SQLite runtime database, React frontend, and Tailwind CSS UI.

## What Is Included

- `schema.sql`: PostgreSQL schema matching the original design deliverable.
- `api.md`: REST API contracts with request parameters and JSON response examples.
- `backend/`: Flask server implementing the documented APIs.
- `backend/schema.sqlite.sql`: SQLite-compatible runtime schema for local development.
- `backend/seed.sql`: Demo season, teams, matches, squads, innings, and standings.
- `frontend/`: React + Tailwind UI for Matches, Points Table, and Teams/Squad.

## Relevant Backend Concepts

The implementation includes concepts that fit this problem statement:

- Server-side pagination for `GET /v1/seasons/{seasonYear}/matches`.
- Infinite scroll in the frontend match list, powered by paginated API calls.
- TTL caching for points table and team/squad reads, because those endpoints are read-heavy and change less frequently than live match data.
- A materialized standings read model in `team_standings`, derived from match results.

## Database Choice

The original assignment asks for an RDBMS schema and prefers PostgreSQL or MySQL. That is why `schema.sql` is PostgreSQL.

For this runnable local app, the Flask backend uses SQLite by default so the project can run without installing a PostgreSQL server. A `.sql` file is only a script; it does not become a usable database by itself. PostgreSQL requires a running PostgreSQL server, then `schema.sql` can be executed against it. SQLite is also an RDBMS, so it is valid for local execution, but use PostgreSQL if the evaluator requires the preferred production database.

## Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend URL:

```text
http://127.0.0.1:5000
```

Example:

```text
http://127.0.0.1:5000/v1/seasons/2025/matches?page=1&pageSize=3
```

## Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## API Endpoints

- `GET /v1/seasons`
- `GET /v1/seasons/{seasonYear}/matches`
- `GET /v1/seasons/{seasonYear}/matches/{matchNumber}`
- `GET /v1/seasons/{seasonYear}/points-table`
- `GET /v1/seasons/{seasonYear}/teams`
- `GET /v1/seasons/{seasonYear}/teams/{teamCode}`

See `api.md` for exact contracts.
