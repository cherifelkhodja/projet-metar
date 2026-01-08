-- METAR Collector Database Schema
-- Version: 1.0.0

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: airports
-- Stores information about monitored airports
CREATE TABLE airports (
    icao_code VARCHAR(4) PRIMARY KEY,
    name VARCHAR(255),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    elevation_ft INTEGER,
    timezone VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: metar_observations
-- Stores parsed METAR data
CREATE TABLE metar_observations (
    id BIGSERIAL PRIMARY KEY,
    icao_code VARCHAR(4) NOT NULL REFERENCES airports(icao_code) ON DELETE CASCADE,
    observation_time TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_metar TEXT NOT NULL,

    -- Wind data
    wind_direction_degrees INTEGER,
    wind_speed_kt INTEGER,
    wind_gust_kt INTEGER,
    wind_variable_from INTEGER,
    wind_variable_to INTEGER,

    -- Visibility
    visibility_statute_mi DECIMAL(5,2),
    visibility_meters INTEGER,

    -- Weather phenomena (JSON array)
    weather_phenomena JSONB DEFAULT '[]'::jsonb,

    -- Cloud layers (JSON array)
    cloud_layers JSONB DEFAULT '[]'::jsonb,
    ceiling_ft INTEGER,

    -- Temperature
    temperature_c DECIMAL(4,1),
    dewpoint_c DECIMAL(4,1),

    -- Pressure
    altimeter_inhg DECIMAL(5,2),
    altimeter_hpa INTEGER,

    -- Flight category
    flight_category VARCHAR(10),

    -- Metadata
    source VARCHAR(50) NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint to prevent duplicates
    CONSTRAINT unique_metar_observation UNIQUE(icao_code, observation_time)
);

-- Table: collection_logs
-- Tracks collection job executions
CREATE TABLE collection_logs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'success', 'partial', 'failed')),
    airports_requested INTEGER DEFAULT 0,
    airports_success INTEGER DEFAULT 0,
    airports_failed INTEGER DEFAULT 0,
    new_observations INTEGER DEFAULT 0,
    duplicates_skipped INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance optimization
CREATE INDEX idx_metar_icao_time ON metar_observations(icao_code, observation_time DESC);
CREATE INDEX idx_metar_time ON metar_observations(observation_time DESC);
CREATE INDEX idx_metar_flight_category ON metar_observations(flight_category);
CREATE INDEX idx_metar_fetched_at ON metar_observations(fetched_at DESC);
CREATE INDEX idx_collection_logs_started_at ON collection_logs(started_at DESC);
CREATE INDEX idx_collection_logs_status ON collection_logs(status);
CREATE INDEX idx_airports_active ON airports(is_active) WHERE is_active = TRUE;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for airports table
CREATE TRIGGER update_airports_updated_at
    BEFORE UPDATE ON airports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE airports IS 'Stores information about monitored airports';
COMMENT ON TABLE metar_observations IS 'Stores parsed METAR observations with structured data';
COMMENT ON TABLE collection_logs IS 'Tracks the execution of collection jobs';
COMMENT ON COLUMN metar_observations.flight_category IS 'VFR, MVFR, IFR, or LIFR based on visibility and ceiling';
COMMENT ON COLUMN metar_observations.weather_phenomena IS 'JSON array of weather phenomena codes';
COMMENT ON COLUMN metar_observations.cloud_layers IS 'JSON array of cloud layer objects with type and altitude';
