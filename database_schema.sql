CREATE TABLE IF NOT EXISTS weather_observations (
  station_id TEXT NOT NULL,
  station_name TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  county_name TEXT,
  town_name TEXT,
  altitude REAL,
  latitude REAL,
  longitude REAL,
  temperature REAL,
  humidity REAL,
  pressure REAL,
  wind_speed REAL,
  wind_direction REAL,
  wind_direction_variable INTEGER NOT NULL,
  precipitation REAL,
  precipitation_status TEXT,
  fetched_at TEXT NOT NULL,

  PRIMARY KEY (station_id, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_weather_observations_observation_at
ON weather_observations (observed_at);

CREATE INDEX IF NOT EXISTS idx_weather_observations_county_time
ON weather_observations (county_name, observed_at);
