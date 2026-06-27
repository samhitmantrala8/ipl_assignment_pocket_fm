# IPL Platform REST API Contracts

Base URL: `/v1`

All responses are JSON. All season paths use the IPL season year, for example `2025`. Team identifiers use stable uppercase `teams.code` values such as `CSK`, `MI`, or `RCB`.

## Common Error Shape

Use this shape for all non-2xx responses:

```json
{
  "error": {
    "code": "not_found",
    "message": "Season 2099 was not found",
    "details": {}
  }
}
```

Common status codes:

- `200 OK`: request succeeded.
- `400 Bad Request`: invalid query parameter or path parameter.
- `404 Not Found`: season, team, or match does not exist.
- `500 Internal Server Error`: unexpected server failure.

## GET /v1/seasons

Return available IPL seasons.

Query parameters: none.

Example response:

```json
{
  "data": [
    {
      "year": 2025,
      "name": "Indian Premier League 2025",
      "startDate": "2025-03-22",
      "endDate": "2025-05-25"
    }
  ]
}
```

## GET /v1/seasons/{seasonYear}/matches

Return a paginated match/results list for one season.

Path parameters:

- `seasonYear` integer, required. Example: `2025`.

Query parameters:

- `page` integer, optional, default `1`, minimum `1`.
- `pageSize` integer, optional, default `20`, minimum `1`, maximum `100`.
- `status` string, optional. One of `upcoming`, `live`, `completed`.
- `teamCode` string, optional. Filters matches where the team is either home or away team.

Sort order: `matchDate DESC`, then `matchNumber DESC`.

Example request:

`GET /v1/seasons/2025/matches?page=1&pageSize=2&status=completed`

Example response:

```json
{
  "data": [
    {
      "matchNumber": 74,
      "matchDate": "2025-05-25T14:00:00Z",
      "venue": {
        "name": "Eden Gardens",
        "city": "Kolkata"
      },
      "teams": {
        "home": {
          "code": "KKR",
          "name": "Kolkata Knight Riders",
          "score": {
            "runs": 184,
            "wickets": 6,
            "overs": "20.0"
          }
        },
        "away": {
          "code": "SRH",
          "name": "Sunrisers Hyderabad",
          "score": {
            "runs": 178,
            "wickets": 8,
            "overs": "20.0"
          }
        }
      },
      "winner": {
        "code": "KKR",
        "name": "Kolkata Knight Riders"
      },
      "status": "completed",
      "resultType": "normal",
      "resultSummary": "Kolkata Knight Riders won by 6 runs"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 2,
    "totalItems": 1,
    "totalPages": 1
  }
}
```

## GET /v1/seasons/{seasonYear}/matches/{matchNumber}

Return one match with full innings scores.

Path parameters:

- `seasonYear` integer, required.
- `matchNumber` integer, required.

Example response:

```json
{
  "data": {
    "matchNumber": 12,
    "matchDate": "2025-04-01T14:00:00Z",
    "venue": {
      "name": "MA Chidambaram Stadium",
      "city": "Chennai"
    },
    "homeTeam": {
      "code": "CSK",
      "name": "Chennai Super Kings"
    },
    "awayTeam": {
      "code": "RCB",
      "name": "Royal Challengers Bengaluru"
    },
    "status": "completed",
    "winner": {
      "code": "CSK",
      "name": "Chennai Super Kings"
    },
    "resultType": "normal",
    "resultSummary": "Chennai Super Kings won by 4 wickets",
    "innings": [
      {
        "inningsNumber": 1,
        "battingTeam": {
          "code": "RCB",
          "name": "Royal Challengers Bengaluru"
        },
        "bowlingTeam": {
          "code": "CSK",
          "name": "Chennai Super Kings"
        },
        "runs": 171,
        "wickets": 7,
        "ballsFaced": 120,
        "overs": "20.0",
        "extras": 9
      },
      {
        "inningsNumber": 2,
        "battingTeam": {
          "code": "CSK",
          "name": "Chennai Super Kings"
        },
        "bowlingTeam": {
          "code": "RCB",
          "name": "Royal Challengers Bengaluru"
        },
        "runs": 172,
        "wickets": 6,
        "ballsFaced": 116,
        "overs": "19.2",
        "extras": 5
      }
    ]
  }
}
```

## GET /v1/seasons/{seasonYear}/points-table

Return the ranked points table for one season.

Path parameters:

- `seasonYear` integer, required.

Sort order: `rank ASC`.

Example response:

```json
{
  "data": [
    {
      "rank": 1,
      "team": {
        "code": "GT",
        "name": "Gujarat Titans",
        "logoUrl": "https://static.iplt20.com/teams/GT.png"
      },
      "played": 14,
      "won": 10,
      "lost": 4,
      "noResult": 0,
      "points": 20,
      "netRunRate": 0.809
    },
    {
      "rank": 2,
      "team": {
        "code": "CSK",
        "name": "Chennai Super Kings",
        "logoUrl": "https://static.iplt20.com/teams/CSK.png"
      },
      "played": 14,
      "won": 9,
      "lost": 5,
      "noResult": 0,
      "points": 18,
      "netRunRate": 0.652
    }
  ],
  "meta": {
    "season": 2025,
    "lastCalculatedAt": "2025-05-18T19:10:00Z"
  }
}
```

## GET /v1/seasons/{seasonYear}/teams

Return teams participating in a season.

Path parameters:

- `seasonYear` integer, required.

Example response:

```json
{
  "data": [
    {
      "code": "MI",
      "name": "Mumbai Indians",
      "homeCity": "Mumbai",
      "captain": {
        "id": 101,
        "name": "Hardik Pandya"
      },
      "logoUrl": "https://static.iplt20.com/teams/MI.png"
    },
    {
      "code": "RR",
      "name": "Rajasthan Royals",
      "homeCity": "Jaipur",
      "captain": {
        "id": 118,
        "name": "Sanju Samson"
      },
      "logoUrl": "https://static.iplt20.com/teams/RR.png"
    }
  ]
}
```

## GET /v1/seasons/{seasonYear}/teams/{teamCode}

Return one team's profile and full squad for a season.

Path parameters:

- `seasonYear` integer, required.
- `teamCode` string, required.

Example response:

```json
{
  "data": {
    "code": "CSK",
    "name": "Chennai Super Kings",
    "homeCity": "Chennai",
    "captain": {
      "id": 201,
      "name": "Ruturaj Gaikwad"
    },
    "logoUrl": "https://static.iplt20.com/teams/CSK.png",
    "squad": [
      {
        "id": 201,
        "name": "Ruturaj Gaikwad",
        "country": "India",
        "role": "batter",
        "isOverseas": false
      },
      {
        "id": 202,
        "name": "MS Dhoni",
        "country": "India",
        "role": "WK",
        "isOverseas": false
      },
      {
        "id": 203,
        "name": "Ravindra Jadeja",
        "country": "India",
        "role": "all-rounder",
        "isOverseas": false
      },
      {
        "id": 204,
        "name": "Matheesha Pathirana",
        "country": "Sri Lanka",
        "role": "bowler",
        "isOverseas": true
      }
    ]
  }
}
```
