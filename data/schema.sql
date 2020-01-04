CREATE TABLE IF NOT EXISTS stats_players(
	name VARCHAR(16) PRIMARY KEY UNIQUE NOT NULL,
	total_points INT,
    total_rank INT,
    team_points INT,
    team_rank INT,
    solo_points INT,
    solo_rank INT,
    country CHAR(3)
);

CREATE TABLE IF NOT EXISTS stats_finishes(
    name VARCHAR(16) NOT NULL,
    timestamp DATE NOT NULL,
    points INT NOT NULL
);

CREATE TABLE IF NOT EXISTS stats_commands(
    guild_id BIGINT,
    channel_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    command VARCHAR(32) NOT NULL
);

CREATE TABLE IF NOT EXISTS records_webhooks(
    id BIGINT PRIMARY KEY UNIQUE NOT NULL,
    token TEXT NOT NULL
);