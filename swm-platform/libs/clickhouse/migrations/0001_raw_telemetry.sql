-- ClickHouse migration: raw telemetry storage and daily aggregates
-- Version: 0001

CREATE TABLE IF NOT EXISTS raw_telemetry (
    imei String CODEC(ZSTD(3)),
    vendor_id UUID,
    device_id UUID,
    vehicle_id UUID,
    event_ts DateTime64(3, 'UTC') CODEC(Delta, ZSTD(3)),
    received_ts DateTime64(3, 'UTC') CODEC(Delta, ZSTD(3)),
    lat Float64 CODEC(ZSTD(3)),
    lng Float64 CODEC(ZSTD(3)),
    speed Float32 CODEC(ZSTD(3)),
    heading UInt16 CODEC(ZSTD(3)),
    altitude Nullable(Float32) CODEC(ZSTD(3)),
    acc_status UInt8 CODEC(ZSTD(3)),
    odometer Nullable(Float64) CODEC(ZSTD(3)),
    fuel_level Nullable(Float32) CODEC(ZSTD(3)),
    payload_json String CODEC(ZSTD(6)),

    INDEX idx_vehicle_id vehicle_id TYPE bloom_filter(0.01) GRANULARITY 64,
    INDEX idx_event_ts event_ts TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_ts)
ORDER BY (vehicle_id, event_ts)
TTL toDateTime(event_ts) + INTERVAL 24 MONTH DELETE
SETTINGS index_granularity = 8192;


CREATE TABLE IF NOT EXISTS raw_telemetry_daily_agg (
    day Date,
    vehicle_id UUID,
    vendor_id UUID,
    points_count UInt64,
    distance_km Float64,
    avg_speed Float64,
    max_speed Float32,
    moving_points UInt64,
    idle_points UInt64,
    first_event_ts DateTime64(3, 'UTC'),
    last_event_ts DateTime64(3, 'UTC')
)
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(day)
ORDER BY (day, vehicle_id, vendor_id)
TTL toDateTime(day) + INTERVAL 24 MONTH DELETE;


CREATE MATERIALIZED VIEW IF NOT EXISTS mv_raw_telemetry_daily_agg
TO raw_telemetry_daily_agg
AS
SELECT
    toDate(event_ts) AS day,
    vehicle_id,
    vendor_id,
    count() AS points_count,
    sum(greatest(speed, 0) / 3600.0) AS distance_km,
    avg(speed) AS avg_speed,
    max(speed) AS max_speed,
    countIf(speed >= 5.0) AS moving_points,
    countIf(speed < 5.0) AS idle_points,
    min(event_ts) AS first_event_ts,
    max(event_ts) AS last_event_ts
FROM raw_telemetry
GROUP BY day, vehicle_id, vendor_id;
