# IPL Platform API Specification

This is the advanced API proposal that pairs with `docs/ADVANCED_SQLITE_SCHEMA_PROPOSAL.sql`.

It is intentionally kept separate from root `api.md` because the current runnable Flask app still implements the original `/v1` API contract.

## Base URL

```text
/api/v1
```

## System Rules And Conventions

- Identifiers: `{year}` maps to `seasons.year`, for example `2024`.
- Team identifier: `{team_slug}` maps to `teams.franchise_slug`.
- Pagination: global query params `page`, default `1`, and `limit`, default `20`.
- Time zones: all timestamps are ISO 8601 extended UTC, for example `YYYY-MM-DDTHH:mm:ssZ`.
- Cricket overs: `overs` are calculated in the server layer from `legal_balls_bowled`, for example `17` legal balls becomes `"2.5"`.

## 1. Get Season Metadata And Accolades

Fetches historical high-level information about a season, including host country, tournament accolades, and champions.

Method and path:

```text
GET /seasons/{year}
```

Response `200 OK`:

```json
{
  "year": 2024,
  "name": "IPL 2024",
  "host_country": "India",
  "start_date": "2024-03-22",
  "end_date": "2024-05-26",
  "accolades": {
    "winner": {
      "slug": "kkr",
      "name": "Kolkata Knight Riders"
    },
    "orange_cap": {
      "player_id": 18,
      "name": "Virat Kohli",
      "team_code": "RCB"
    },
    "purple_cap": {
      "player_id": 47,
      "name": "Harshal Patel",
      "team_code": "PBKS"
    }
  }
}
```

## 2. Get Matches / Results

Retrieves a paginated list of fixtures. This endpoint exposes the match stage, league versus playoff, and DLS target details for rain-affected games.

Method and path:

```text
GET /seasons/{year}/matches
```

Query parameters:

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `page` | integer | `1` | Page number. |
| `limit` | integer | `20` | Page size. |
| `stage` | string | none | Optional. One of `league`, `playoff`. |

Response `200 OK`:

```json
{
  "meta": {
    "page": 1,
    "limit": 20,
    "total_count": 74
  },
  "data": [
    {
      "match_number": 74,
      "stage": "playoff",
      "playoff_tag": "Final",
      "date": "2024-05-26T14:00:00Z",
      "status": "completed",
      "venue": {
        "name": "MA Chidambaram Stadium",
        "city": "Chennai",
        "country": "India"
      },
      "teams": {
        "home": {
          "slug": "srh",
          "code": "SRH",
          "name": "Sunrisers Hyderabad",
          "logo_url": "https://assets.iplt20.com/srh.png"
        },
        "away": {
          "slug": "kkr",
          "code": "KKR",
          "name": "Kolkata Knight Riders",
          "logo_url": "https://assets.iplt20.com/kkr.png"
        }
      },
      "toss": {
        "winner_slug": "srh",
        "decision": "bat"
      },
      "result": {
        "winner_slug": "kkr",
        "type": "normal",
        "is_dls_applied": false,
        "target_runs": 114,
        "win_margin": 8,
        "win_margin_type": "wickets",
        "balls_remaining": 57,
        "summary": "KKR won by 8 wickets"
      },
      "innings": [
        {
          "innings_number": 1,
          "batting_team_slug": "srh",
          "runs": 113,
          "wickets": 10,
          "overs": "18.3",
          "legal_balls_bowled": 111,
          "extras": 5
        },
        {
          "innings_number": 2,
          "batting_team_slug": "kkr",
          "runs": 114,
          "wickets": 2,
          "overs": "10.3",
          "legal_balls_bowled": 63,
          "extras": 2
        }
      ],
      "live_metadata": null
    }
  ]
}
```

### Handling Live Match Status With DLS

If `status` is `live`, the `result` block is `null` and `live_metadata` is populated. In a rain interruption where overs are lost, `is_dls_applied` becomes `true` and `target_runs` updates in real time.

Example live metadata:

```json
{
  "live_metadata": {
    "current_innings": 2,
    "current_batting_team_slug": "csk",
    "current_bowling_team_slug": "gt",
    "is_dls_applied": true,
    "target_runs": 171,
    "dls_par_score": 150,
    "runs_required": 21,
    "balls_remaining": 15
  }
}
```

## 3. Get Points Table

Retrieves ranked regular-season standings. Sorting uses points, NRR, and the pre-computed database tie-breaker `wickets_per_fair_delivery`.

Method and path:

```text
GET /seasons/{year}/standings
```

Response `200 OK`:

```json
{
  "season_year": 2024,
  "last_calculated_at": "2024-05-19T22:00:00Z",
  "standings": [
    {
      "rank": 1,
      "team": {
        "slug": "kkr",
        "code": "KKR",
        "name": "Kolkata Knight Riders",
        "logo_url": "https://assets.iplt20.com/kkr.png"
      },
      "matches_played": 14,
      "won": 9,
      "lost": 3,
      "no_result": 2,
      "points": 20,
      "net_run_rate": 1.428,
      "wickets_per_fair_delivery": 0.065
    }
  ]
}
```

## 4. Get Team Profile

Fetches lightweight brand profile details for a franchise slot in a given season. This keeps navigation payloads small.

Method and path:

```text
GET /seasons/{year}/teams/{team_slug}
```

Response `200 OK`:

```json
{
  "slug": "mi",
  "code": "MI",
  "name": "Mumbai Indians",
  "home_city": "Mumbai",
  "primary_home_venue": {
    "name": "Wankhede Stadium",
    "city": "Mumbai"
  },
  "logo_url": "https://assets.iplt20.com/mi.png",
  "captain": {
    "player_id": 45,
    "name": "Hardik Pandya"
  }
}
```

## 5. Get Team Squad

Loads squad player data separately from the lightweight team profile. This keeps profile navigation fast and lets clients request squad data only when needed.

Method and path:

```text
GET /seasons/{year}/teams/{team_slug}/squad
```

Response `200 OK`:

```json
{
  "team_slug": "mi",
  "season_year": 2024,
  "squad": [
    {
      "player_id": 45,
      "name": "Hardik Pandya",
      "country": "India",
      "is_overseas": false,
      "role": "all-rounder",
      "batting_style": "Right-hand bat",
      "bowling_style": "Right-arm fast-medium",
      "shirt_number": 33
    },
    {
      "player_id": 93,
      "name": "Jasprit Bumrah",
      "country": "India",
      "is_overseas": false,
      "role": "bowler",
      "batting_style": "Right-hand bat",
      "bowling_style": "Right-arm fast",
      "shirt_number": 93
    },
    {
      "player_id": 63,
      "name": "Suryakumar Yadav",
      "country": "India",
      "is_overseas": false,
      "role": "batter",
      "batting_style": "Right-hand bat",
      "bowling_style": "Right-arm offbreak",
      "shirt_number": 63
    },
    {
      "player_id": 74,
      "name": "Ishan Kishan",
      "country": "India",
      "is_overseas": false,
      "role": "WK",
      "batting_style": "Left-hand bat",
      "bowling_style": null,
      "shirt_number": 32
    },
    {
      "player_id": 112,
      "name": "Tim David",
      "country": "Australia",
      "is_overseas": true,
      "role": "batter",
      "batting_style": "Right-hand bat",
      "bowling_style": "Right-arm offbreak",
      "shirt_number": 8
    }
  ]
}
```
