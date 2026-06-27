PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL UNIQUE CHECK (year BETWEEN 2008 AND 2100),
    name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    CHECK (start_date <= end_date)
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    home_city TEXT NOT NULL,
    logo_url TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    UNIQUE (name, city)
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    country TEXT NOT NULL,
    batting_style TEXT,
    bowling_style TEXT,
    UNIQUE (full_name, country)
);

CREATE TABLE IF NOT EXISTS team_seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    captain_player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    UNIQUE (season_id, team_id)
);

CREATE TABLE IF NOT EXISTS squad_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_season_id INTEGER NOT NULL REFERENCES team_seasons(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    player_role TEXT NOT NULL CHECK (player_role IN ('batter', 'bowler', 'all-rounder', 'WK')),
    shirt_number INTEGER CHECK (shirt_number BETWEEN 0 AND 999),
    is_overseas INTEGER NOT NULL DEFAULT 0,
    UNIQUE (team_season_id, player_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    match_number INTEGER NOT NULL CHECK (match_number > 0),
    match_date TEXT NOT NULL,
    venue_id INTEGER NOT NULL REFERENCES venues(id) ON DELETE RESTRICT,
    home_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    away_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    toss_winner_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    winner_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK (status IN ('upcoming', 'live', 'completed')),
    result_type TEXT NOT NULL DEFAULT 'normal' CHECK (
        result_type IN ('normal', 'tie', 'no_result', 'abandoned', 'walkover')
    ),
    result_summary TEXT,
    started_at TEXT,
    completed_at TEXT,
    UNIQUE (season_id, match_number),
    CHECK (home_team_id <> away_team_id)
);

CREATE TABLE IF NOT EXISTS innings_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    innings_number INTEGER NOT NULL CHECK (innings_number BETWEEN 1 AND 4),
    batting_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    bowling_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    runs INTEGER NOT NULL DEFAULT 0 CHECK (runs >= 0),
    wickets INTEGER NOT NULL DEFAULT 0 CHECK (wickets BETWEEN 0 AND 10),
    balls_faced INTEGER NOT NULL DEFAULT 0 CHECK (balls_faced BETWEEN 0 AND 180),
    extras INTEGER NOT NULL DEFAULT 0 CHECK (extras >= 0),
    UNIQUE (match_id, innings_number),
    CHECK (batting_team_id <> bowling_team_id)
);

CREATE TABLE IF NOT EXISTS team_standings (
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL CHECK (rank > 0),
    matches_played INTEGER NOT NULL DEFAULT 0 CHECK (matches_played >= 0),
    won INTEGER NOT NULL DEFAULT 0 CHECK (won >= 0),
    lost INTEGER NOT NULL DEFAULT 0 CHECK (lost >= 0),
    no_result INTEGER NOT NULL DEFAULT 0 CHECK (no_result >= 0),
    points INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    net_run_rate REAL NOT NULL DEFAULT 0.000,
    last_calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (season_id, team_id),
    UNIQUE (season_id, rank),
    CHECK (matches_played = won + lost + no_result)
);

CREATE TABLE IF NOT EXISTS standings_refresh_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER REFERENCES seasons(id) ON DELETE SET NULL,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    matches_scanned INTEGER NOT NULL DEFAULT 0 CHECK (matches_scanned >= 0),
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_matches_season_date ON matches (season_id, match_date DESC, match_number);
CREATE INDEX IF NOT EXISTS idx_matches_season_status ON matches (season_id, status);
CREATE INDEX IF NOT EXISTS idx_innings_match ON innings_scores (match_id, innings_number);
CREATE INDEX IF NOT EXISTS idx_squad_team_season_role ON squad_members (team_season_id, player_role);
CREATE INDEX IF NOT EXISTS idx_standings_season_rank ON team_standings (season_id, rank);
CREATE INDEX IF NOT EXISTS idx_standings_refresh_started ON standings_refresh_runs (started_at DESC);
