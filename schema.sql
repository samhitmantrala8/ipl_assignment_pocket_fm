-- PostgreSQL schema for IPL Platform API Design.
-- Source of truth is normalized match/team/player data. The standings table is
-- a materialized read model maintained from completed match results.

CREATE TABLE seasons (
    id BIGSERIAL PRIMARY KEY,
    year SMALLINT NOT NULL UNIQUE CHECK (year BETWEEN 2008 AND 2100),
    name VARCHAR(80) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    CHECK (start_date <= end_date)
);

CREATE TABLE teams (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL UNIQUE,
    home_city VARCHAR(80) NOT NULL,
    logo_url TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE venues (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    city VARCHAR(80) NOT NULL,
    country VARCHAR(80) NOT NULL DEFAULT 'India',
    UNIQUE (name, city)
);

CREATE TABLE players (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    country VARCHAR(80) NOT NULL,
    batting_style VARCHAR(80),
    bowling_style VARCHAR(80),
    UNIQUE (full_name, country)
);

CREATE TABLE team_seasons (
    id BIGSERIAL PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id BIGINT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    captain_player_id BIGINT REFERENCES players(id) ON DELETE SET NULL,
    UNIQUE (season_id, team_id)
);

CREATE TABLE squad_members (
    id BIGSERIAL PRIMARY KEY,
    team_season_id BIGINT NOT NULL REFERENCES team_seasons(id) ON DELETE CASCADE,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE RESTRICT,
    player_role VARCHAR(20) NOT NULL CHECK (
        player_role IN ('batter', 'bowler', 'all-rounder', 'WK')
    ),
    shirt_number SMALLINT CHECK (shirt_number BETWEEN 0 AND 999),
    is_overseas BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (team_season_id, player_id)
);

CREATE TABLE matches (
    id BIGSERIAL PRIMARY KEY,
    season_id BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    match_number INTEGER NOT NULL CHECK (match_number > 0),
    match_date TIMESTAMPTZ NOT NULL,
    venue_id BIGINT NOT NULL REFERENCES venues(id) ON DELETE RESTRICT,
    home_team_id BIGINT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    away_team_id BIGINT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    toss_winner_team_id BIGINT REFERENCES teams(id) ON DELETE SET NULL,
    winner_team_id BIGINT REFERENCES teams(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('upcoming', 'live', 'completed')),
    result_type VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (
        result_type IN ('normal', 'tie', 'no_result', 'abandoned', 'walkover')
    ),
    result_summary TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE (season_id, match_number),
    CHECK (home_team_id <> away_team_id),
    CHECK (
        status <> 'completed'
        OR result_type IN ('normal', 'tie', 'no_result', 'abandoned', 'walkover')
    )
);

CREATE TABLE innings_scores (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    innings_number SMALLINT NOT NULL CHECK (innings_number BETWEEN 1 AND 4),
    batting_team_id BIGINT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    bowling_team_id BIGINT NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    runs INTEGER NOT NULL DEFAULT 0 CHECK (runs >= 0),
    wickets SMALLINT NOT NULL DEFAULT 0 CHECK (wickets BETWEEN 0 AND 10),
    balls_faced SMALLINT NOT NULL DEFAULT 0 CHECK (balls_faced BETWEEN 0 AND 180),
    extras INTEGER NOT NULL DEFAULT 0 CHECK (extras >= 0),
    UNIQUE (match_id, innings_number),
    CHECK (batting_team_id <> bowling_team_id)
);

CREATE TABLE team_standings (
    season_id BIGINT NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    team_id BIGINT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL CHECK (rank > 0),
    matches_played INTEGER NOT NULL DEFAULT 0 CHECK (matches_played >= 0),
    won INTEGER NOT NULL DEFAULT 0 CHECK (won >= 0),
    lost INTEGER NOT NULL DEFAULT 0 CHECK (lost >= 0),
    no_result INTEGER NOT NULL DEFAULT 0 CHECK (no_result >= 0),
    points INTEGER NOT NULL DEFAULT 0 CHECK (points >= 0),
    net_run_rate NUMERIC(6, 3) NOT NULL DEFAULT 0.000,
    last_calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (season_id, team_id),
    UNIQUE (season_id, rank),
    CHECK (matches_played = won + lost + no_result)
);

CREATE INDEX idx_matches_season_date ON matches (season_id, match_date DESC, match_number);
CREATE INDEX idx_matches_season_status ON matches (season_id, status);
CREATE INDEX idx_matches_home_team ON matches (home_team_id);
CREATE INDEX idx_matches_away_team ON matches (away_team_id);
CREATE INDEX idx_innings_match ON innings_scores (match_id, innings_number);
CREATE INDEX idx_squad_team_season_role ON squad_members (team_season_id, player_role);
CREATE INDEX idx_standings_season_rank ON team_standings (season_id, rank);
