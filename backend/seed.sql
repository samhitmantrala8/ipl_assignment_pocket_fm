INSERT INTO seasons (id, year, name, start_date, end_date) VALUES
(1, 2025, 'Indian Premier League 2025', '2025-03-22', '2025-05-25');

INSERT INTO teams (id, code, name, home_city, logo_url) VALUES
(1, 'CSK', 'Chennai Super Kings', 'Chennai', 'https://static.iplt20.com/teams/CSK.png'),
(2, 'MI', 'Mumbai Indians', 'Mumbai', 'https://static.iplt20.com/teams/MI.png'),
(3, 'RCB', 'Royal Challengers Bengaluru', 'Bengaluru', 'https://static.iplt20.com/teams/RCB.png'),
(4, 'KKR', 'Kolkata Knight Riders', 'Kolkata', 'https://static.iplt20.com/teams/KKR.png'),
(5, 'SRH', 'Sunrisers Hyderabad', 'Hyderabad', 'https://static.iplt20.com/teams/SRH.png'),
(6, 'GT', 'Gujarat Titans', 'Ahmedabad', 'https://static.iplt20.com/teams/GT.png');

INSERT INTO venues (id, name, city, country) VALUES
(1, 'MA Chidambaram Stadium', 'Chennai', 'India'),
(2, 'Wankhede Stadium', 'Mumbai', 'India'),
(3, 'M. Chinnaswamy Stadium', 'Bengaluru', 'India'),
(4, 'Eden Gardens', 'Kolkata', 'India'),
(5, 'Rajiv Gandhi International Stadium', 'Hyderabad', 'India'),
(6, 'Narendra Modi Stadium', 'Ahmedabad', 'India');

INSERT INTO players (id, full_name, country, batting_style, bowling_style) VALUES
(1, 'Ruturaj Gaikwad', 'India', 'Right-hand bat', NULL),
(2, 'MS Dhoni', 'India', 'Right-hand bat', NULL),
(3, 'Ravindra Jadeja', 'India', 'Left-hand bat', 'Left-arm orthodox'),
(4, 'Matheesha Pathirana', 'Sri Lanka', 'Right-hand bat', 'Right-arm fast'),
(5, 'Hardik Pandya', 'India', 'Right-hand bat', 'Right-arm medium'),
(6, 'Rohit Sharma', 'India', 'Right-hand bat', NULL),
(7, 'Suryakumar Yadav', 'India', 'Right-hand bat', NULL),
(8, 'Jasprit Bumrah', 'India', 'Right-hand bat', 'Right-arm fast'),
(9, 'Faf du Plessis', 'South Africa', 'Right-hand bat', NULL),
(10, 'Virat Kohli', 'India', 'Right-hand bat', NULL),
(11, 'Dinesh Karthik', 'India', 'Right-hand bat', NULL),
(12, 'Mohammed Siraj', 'India', 'Right-hand bat', 'Right-arm fast'),
(13, 'Shreyas Iyer', 'India', 'Right-hand bat', NULL),
(14, 'Andre Russell', 'West Indies', 'Right-hand bat', 'Right-arm fast'),
(15, 'Sunil Narine', 'West Indies', 'Left-hand bat', 'Right-arm offbreak'),
(16, 'Rinku Singh', 'India', 'Left-hand bat', NULL),
(17, 'Pat Cummins', 'Australia', 'Right-hand bat', 'Right-arm fast'),
(18, 'Travis Head', 'Australia', 'Left-hand bat', 'Right-arm offbreak'),
(19, 'Heinrich Klaasen', 'South Africa', 'Right-hand bat', NULL),
(20, 'Bhuvneshwar Kumar', 'India', 'Right-hand bat', 'Right-arm medium'),
(21, 'Shubman Gill', 'India', 'Right-hand bat', NULL),
(22, 'Rashid Khan', 'Afghanistan', 'Right-hand bat', 'Right-arm legbreak'),
(23, 'David Miller', 'South Africa', 'Left-hand bat', NULL),
(24, 'Mohammed Shami', 'India', 'Right-hand bat', 'Right-arm fast');

INSERT INTO team_seasons (id, season_id, team_id, captain_player_id) VALUES
(1, 1, 1, 1),
(2, 1, 2, 5),
(3, 1, 3, 9),
(4, 1, 4, 13),
(5, 1, 5, 17),
(6, 1, 6, 21);

INSERT INTO squad_members (team_season_id, player_id, player_role, is_overseas) VALUES
(1, 1, 'batter', 0), (1, 2, 'WK', 0), (1, 3, 'all-rounder', 0), (1, 4, 'bowler', 1),
(2, 5, 'all-rounder', 0), (2, 6, 'batter', 0), (2, 7, 'batter', 0), (2, 8, 'bowler', 0),
(3, 9, 'batter', 1), (3, 10, 'batter', 0), (3, 11, 'WK', 0), (3, 12, 'bowler', 0),
(4, 13, 'batter', 0), (4, 14, 'all-rounder', 1), (4, 15, 'all-rounder', 1), (4, 16, 'batter', 0),
(5, 17, 'bowler', 1), (5, 18, 'batter', 1), (5, 19, 'WK', 1), (5, 20, 'bowler', 0),
(6, 21, 'batter', 0), (6, 22, 'all-rounder', 1), (6, 23, 'batter', 1), (6, 24, 'bowler', 0);

INSERT INTO matches (
    id, season_id, match_number, match_date, venue_id, home_team_id, away_team_id,
    toss_winner_team_id, winner_team_id, status, result_type, result_summary, started_at, completed_at
) VALUES
(1, 1, 1, '2025-03-22T14:00:00Z', 1, 1, 3, 3, 1, 'completed', 'normal', 'Chennai Super Kings won by 4 wickets', '2025-03-22T14:00:00Z', '2025-03-22T18:05:00Z'),
(2, 1, 2, '2025-03-23T14:00:00Z', 2, 2, 6, 2, 6, 'completed', 'normal', 'Gujarat Titans won by 12 runs', '2025-03-23T14:00:00Z', '2025-03-23T18:02:00Z'),
(3, 1, 3, '2025-03-24T14:00:00Z', 4, 4, 5, 5, 4, 'completed', 'normal', 'Kolkata Knight Riders won by 6 runs', '2025-03-24T14:00:00Z', '2025-03-24T18:10:00Z'),
(4, 1, 4, '2025-03-26T14:00:00Z', 6, 6, 1, 1, NULL, 'completed', 'no_result', 'Match abandoned due to rain', '2025-03-26T14:00:00Z', '2025-03-26T15:15:00Z'),
(5, 1, 5, '2025-03-28T14:00:00Z', 3, 3, 2, NULL, NULL, 'live', 'normal', NULL, '2025-03-28T14:00:00Z', NULL),
(6, 1, 6, '2025-03-30T14:00:00Z', 5, 5, 1, NULL, NULL, 'upcoming', 'normal', NULL, NULL, NULL),
(7, 1, 7, '2025-04-01T14:00:00Z', 4, 4, 6, NULL, NULL, 'upcoming', 'normal', NULL, NULL, NULL),
(8, 1, 8, '2025-04-03T14:00:00Z', 2, 2, 1, NULL, NULL, 'upcoming', 'normal', NULL, NULL, NULL);

INSERT INTO innings_scores (match_id, innings_number, batting_team_id, bowling_team_id, runs, wickets, balls_faced, extras) VALUES
(1, 1, 3, 1, 171, 7, 120, 9),
(1, 2, 1, 3, 172, 6, 116, 5),
(2, 1, 6, 2, 188, 5, 120, 8),
(2, 2, 2, 6, 176, 8, 120, 7),
(3, 1, 4, 5, 184, 6, 120, 10),
(3, 2, 5, 4, 178, 8, 120, 6),
(5, 1, 3, 2, 96, 3, 72, 4);

INSERT INTO team_standings (
    season_id, team_id, rank, matches_played, won, lost, no_result, points, net_run_rate, last_calculated_at
) VALUES
(1, 6, 1, 2, 1, 0, 1, 3, 0.600, '2025-03-26T19:00:00Z'),
(1, 1, 2, 2, 1, 0, 1, 3, 0.245, '2025-03-26T19:00:00Z'),
(1, 4, 3, 1, 1, 0, 0, 2, 0.300, '2025-03-26T19:00:00Z'),
(1, 5, 4, 1, 0, 1, 0, 0, -0.300, '2025-03-26T19:00:00Z'),
(1, 2, 5, 1, 0, 1, 0, 0, -0.600, '2025-03-26T19:00:00Z'),
(1, 3, 6, 1, 0, 1, 0, 0, -0.245, '2025-03-26T19:00:00Z');
