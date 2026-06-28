PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL UNIQUE CHECK (year BETWEEN 2008 AND 2100),
    name TEXT NOT NULL,
    host_country TEXT NOT NULL DEFAULT 'India',
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,

    -- Historical season awards (derived at season end, NULL allowed for active seasons)
    winner_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    orange_cap_player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    purple_cap_player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,

    CHECK (start_date <= end_date)
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    franchise_slug TEXT NOT NULL UNIQUE,  -- Immutable anchor (e.g., 'rcb', 'mi', 'dc')
    home_city TEXT NOT NULL,              -- Permanent brand city
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
    date_of_birth TEXT NOT NULL,
    batting_style TEXT,
    bowling_style TEXT,
    -- Combined with DOB to prevent identical name collisions
    UNIQUE (full_name, country, date_of_birth)
);

CREATE TABLE IF NOT EXISTS team_seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    team_code TEXT NOT NULL,              -- Seasonal short code (e.g., 'DD' vs 'DC')
    team_name TEXT NOT NULL,              -- Seasonal name
    logo_url TEXT NOT NULL,

    -- Tracks where they actually host their home games THIS season (UAE, SA, etc.)
    primary_home_venue_id INTEGER REFERENCES venues(id) ON DELETE SET NULL,

    captain_player_id INTEGER REFERENCES players(id) ON DELETE SET NULL,
    UNIQUE (season_id, team_id),
    UNIQUE (season_id, team_code)
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
    CHECK (home_team_id <> away_team_id),

    -- Differentiates between league phase and knockouts
    stage TEXT NOT NULL DEFAULT 'league' CHECK (stage IN ('league', 'playoff')),

    toss_winner_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    toss_decision TEXT CHECK (toss_decision IN ('bat', 'field')),

    status TEXT NOT NULL CHECK (status IN ('upcoming', 'live', 'completed')),
    result_type TEXT NOT NULL DEFAULT 'normal' CHECK (
        result_type IN ('normal', 'tie', 'no_result', 'abandoned', 'walkover')
    ),

    winner_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    is_dls_applied INTEGER NOT NULL DEFAULT 0,

    -- Derived match metrics (No strict CHECK constraints to prevent insertion blocks)
    target_runs INTEGER,
    win_margin INTEGER,
    win_margin_type TEXT,
    balls_remaining INTEGER,
    result_summary TEXT,

    started_at TEXT,
    completed_at TEXT,

    UNIQUE (season_id, match_number)
);

CREATE TABLE IF NOT EXISTS innings_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    innings_number INTEGER NOT NULL CHECK (innings_number > 0), -- Unbound to handle Super Overs

    batting_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    bowling_team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    CHECK (batting_team_id <> bowling_team_id),

    runs INTEGER NOT NULL DEFAULT 0 CHECK (runs >= 0),
    wickets INTEGER NOT NULL DEFAULT 0 CHECK (wickets BETWEEN 0 AND 10),
    legal_balls_bowled INTEGER NOT NULL DEFAULT 0 CHECK (legal_balls_bowled >= 0),
    extras INTEGER NOT NULL DEFAULT 0 CHECK (extras >= 0),

    UNIQUE (match_id, innings_number)
);

CREATE TABLE IF NOT EXISTS team_standings (
    season_id INTEGER NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,

    -- Entirely derived dataset; NO restrictive CHECK constraints to allow seamless background updates
    rank INTEGER NOT NULL,
    matches_played INTEGER NOT NULL DEFAULT 0,
    won INTEGER NOT NULL DEFAULT 0,
    lost INTEGER NOT NULL DEFAULT 0,
    no_result INTEGER NOT NULL DEFAULT 0,
    points INTEGER NOT NULL DEFAULT 0,
    net_run_rate REAL NOT NULL DEFAULT 0.000,

    -- Pre-computed final tie-breaker metric to keep API reads blazing fast
    wickets_per_fair_delivery REAL NOT NULL DEFAULT 0.000,

    last_calculated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (season_id, team_id)
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

-- Indexing for high-frequency queries
CREATE INDEX IF NOT EXISTS idx_matches_season_date ON matches (season_id, match_date DESC, match_number);
CREATE INDEX IF NOT EXISTS idx_matches_season_status ON matches (season_id, status);
CREATE INDEX IF NOT EXISTS idx_matches_season_stage ON matches (season_id, stage);
CREATE INDEX IF NOT EXISTS idx_innings_match ON innings_scores (match_id, innings_number);
CREATE INDEX IF NOT EXISTS idx_squad_team_season_role ON squad_members (team_season_id, player_role);
CREATE INDEX IF NOT EXISTS idx_standings_season_rank ON team_standings (season_id, rank);
CREATE INDEX IF NOT EXISTS idx_standings_refresh_started ON standings_refresh_runs (started_at DESC);

/*
SUMMARY OF ITERATIVE CHANGES:
Reverted to pure SQLite syntax while implementing crucial cricket domain logic and structural fixes. Anchored franchise identity via an immutable `franchise_slug` in `teams` while migrating seasonal branding and dynamic home venues to `team_seasons`. Resolved player name collisions by including `date_of_birth` in the unique constraint. Lifted restrictive `CHECK` constraints on derived columns and `innings_number` to smoothly handle edge cases like multi-Super Overs and background standings recalculations. Enhanced historical data tracking by adding tournament stage flags, structured toss/win margins, season-level accolades (winner, orange/purple caps, host country), and pre-computing the `wickets_per_fair_delivery` tie-breaker directly into the standings for instant API retrieval.
*/
