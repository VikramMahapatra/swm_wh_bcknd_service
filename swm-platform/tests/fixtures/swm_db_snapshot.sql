--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Debian 16.4-1.pgdg110+2)
-- Dumped by pg_dump version 16.4 (Debian 16.4-1.pgdg110+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: tiger; Type: SCHEMA; Schema: -; Owner: swm
--

CREATE SCHEMA tiger;


ALTER SCHEMA tiger OWNER TO swm;

--
-- Name: tiger_data; Type: SCHEMA; Schema: -; Owner: swm
--

CREATE SCHEMA tiger_data;


ALTER SCHEMA tiger_data OWNER TO swm;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: swm
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO swm;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: swm
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: postgis_tiger_geocoder; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder WITH SCHEMA tiger;


--
-- Name: EXTENSION postgis_tiger_geocoder; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_tiger_geocoder IS 'PostGIS tiger geocoder and reverse geocoder';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO swm;

--
-- Name: alert_actions; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.alert_actions (
    id uuid NOT NULL,
    alert_id uuid NOT NULL,
    action_type character varying(32) NOT NULL,
    actor character varying(128) NOT NULL,
    notes character varying(2000),
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_alert_actions_type CHECK (((action_type)::text = ANY ((ARRAY['created'::character varying, 'acknowledged'::character varying, 'resolved'::character varying, 'escalated'::character varying, 'updated'::character varying, 'commented'::character varying])::text[])))
);


ALTER TABLE public.alert_actions OWNER TO swm;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.alerts (
    id uuid NOT NULL,
    alert_type character varying(64) NOT NULL,
    category character varying(64) NOT NULL,
    title character varying(255) NOT NULL,
    message character varying(2000),
    severity character varying(16) DEFAULT 'medium'::character varying NOT NULL,
    status character varying(16) DEFAULT 'open'::character varying NOT NULL,
    escalation_status character varying(64) DEFAULT 'none'::character varying NOT NULL,
    vehicle_id character varying(128),
    imei character varying(17),
    vendor_id uuid,
    route_id uuid,
    ward_id uuid,
    triggered_at timestamp with time zone NOT NULL,
    acknowledged_at timestamp with time zone,
    acknowledged_by character varying(128),
    resolved_at timestamp with time zone,
    resolved_by character varying(128),
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_alerts_severity CHECK (((severity)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_alerts_status CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'acknowledged'::character varying, 'resolved'::character varying, 'escalated'::character varying])::text[])))
);


ALTER TABLE public.alerts OWNER TO swm;

--
-- Name: analytics_daily_kpis; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.analytics_daily_kpis (
    metric_date date NOT NULL,
    vehicle_id character varying(128) NOT NULL,
    imei character varying(17) NOT NULL,
    vendor_id character varying(64) NOT NULL,
    trips_count integer DEFAULT 0 NOT NULL,
    distance_km double precision DEFAULT '0'::double precision NOT NULL,
    runtime_seconds integer DEFAULT 0 NOT NULL,
    moving_seconds integer DEFAULT 0 NOT NULL,
    idle_seconds integer DEFAULT 0 NOT NULL,
    stoppages_count integer DEFAULT 0 NOT NULL,
    overspeed_count integer DEFAULT 0 NOT NULL,
    geofence_entries integer DEFAULT 0 NOT NULL,
    geofence_exits integer DEFAULT 0 NOT NULL,
    route_deviation_count integer DEFAULT 0 NOT NULL,
    fuel_used_l double precision DEFAULT '0'::double precision NOT NULL,
    utilization_pct double precision DEFAULT '0'::double precision NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.analytics_daily_kpis OWNER TO swm;

--
-- Name: analytics_geofence_events; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.analytics_geofence_events (
    id uuid NOT NULL,
    vehicle_id character varying(128) NOT NULL,
    imei character varying(17) NOT NULL,
    device_id character varying(128) NOT NULL,
    vendor_id character varying(64) NOT NULL,
    geofence_id uuid,
    geofence_code character varying(32),
    geofence_type character varying(16),
    event_type character varying(16) NOT NULL,
    event_ts timestamp with time zone NOT NULL,
    dwell_seconds integer,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_analytics_geofence_event_type CHECK (((event_type)::text = ANY ((ARRAY['entry'::character varying, 'exit'::character varying, 'route_deviation'::character varying])::text[])))
);


ALTER TABLE public.analytics_geofence_events OWNER TO swm;

--
-- Name: analytics_idle_records; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.analytics_idle_records (
    id uuid NOT NULL,
    vehicle_id character varying(128) NOT NULL,
    imei character varying(17) NOT NULL,
    device_id character varying(128) NOT NULL,
    vendor_id character varying(64) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone NOT NULL,
    duration_seconds integer NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.analytics_idle_records OWNER TO swm;

--
-- Name: analytics_overspeed_events; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.analytics_overspeed_events (
    id uuid NOT NULL,
    vehicle_id character varying(128) NOT NULL,
    imei character varying(17) NOT NULL,
    device_id character varying(128) NOT NULL,
    vendor_id character varying(64) NOT NULL,
    event_ts timestamp with time zone NOT NULL,
    speed_kph double precision NOT NULL,
    threshold_kph double precision NOT NULL,
    severity character varying(16) NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.analytics_overspeed_events OWNER TO swm;

--
-- Name: analytics_trip_records; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.analytics_trip_records (
    id uuid NOT NULL,
    vehicle_id character varying(128) NOT NULL,
    imei character varying(17) NOT NULL,
    device_id character varying(128) NOT NULL,
    vendor_id character varying(64) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone NOT NULL,
    runtime_seconds integer DEFAULT 0 NOT NULL,
    moving_seconds integer DEFAULT 0 NOT NULL,
    idle_seconds integer DEFAULT 0 NOT NULL,
    stoppages_count integer DEFAULT 0 NOT NULL,
    start_odometer_km double precision,
    end_odometer_km double precision,
    distance_km double precision DEFAULT '0'::double precision NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.analytics_trip_records OWNER TO swm;

--
-- Name: analytics_vehicle_state; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.analytics_vehicle_state (
    vehicle_id character varying(128) NOT NULL,
    imei character varying(17) NOT NULL,
    device_id character varying(128) NOT NULL,
    last_event_ts timestamp with time zone NOT NULL,
    last_lat double precision NOT NULL,
    last_lng double precision NOT NULL,
    last_speed_kph double precision DEFAULT '0'::double precision NOT NULL,
    last_odometer_km double precision,
    last_ignition boolean DEFAULT false NOT NULL,
    trip_active boolean DEFAULT false NOT NULL,
    trip_started_at timestamp with time zone,
    trip_start_odometer_km double precision,
    trip_distance_km double precision DEFAULT '0'::double precision NOT NULL,
    trip_runtime_seconds integer DEFAULT 0 NOT NULL,
    trip_moving_seconds integer DEFAULT 0 NOT NULL,
    trip_idle_seconds integer DEFAULT 0 NOT NULL,
    trip_stoppages integer DEFAULT 0 NOT NULL,
    idle_active boolean DEFAULT false NOT NULL,
    idle_started_at timestamp with time zone,
    idle_anchor_lat double precision,
    idle_anchor_lng double precision,
    current_geofence_code character varying(32),
    current_geofence_entered_at timestamp with time zone,
    last_route_deviation_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.analytics_vehicle_state OWNER TO swm;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.audit_logs (
    id uuid NOT NULL,
    entity_type character varying(64) NOT NULL,
    entity_id character varying(128) NOT NULL,
    action character varying(64) NOT NULL,
    actor character varying(128) NOT NULL,
    before jsonb,
    after jsonb,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO swm;

--
-- Name: auth_permissions; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.auth_permissions (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    created_by character varying(255),
    updated_by character varying(255),
    permission_key character varying(128) NOT NULL,
    permission_name character varying(255) NOT NULL,
    description character varying(1000),
    active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.auth_permissions OWNER TO swm;

--
-- Name: auth_refresh_tokens; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.auth_refresh_tokens (
    id uuid NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(128) NOT NULL,
    token_family_id uuid NOT NULL,
    issued_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    last_used_at timestamp with time zone,
    user_agent character varying(500),
    ip_address character varying(64),
    replaced_by_token_id uuid
);


ALTER TABLE public.auth_refresh_tokens OWNER TO swm;

--
-- Name: auth_role_permissions; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.auth_role_permissions (
    role_id uuid NOT NULL,
    permission_id uuid NOT NULL,
    assigned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assigned_by character varying(255)
);


ALTER TABLE public.auth_role_permissions OWNER TO swm;

--
-- Name: auth_roles; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.auth_roles (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    created_by character varying(255),
    updated_by character varying(255),
    role_key character varying(64) NOT NULL,
    role_name character varying(255) NOT NULL,
    description character varying(1000),
    active boolean DEFAULT true NOT NULL
);


ALTER TABLE public.auth_roles OWNER TO swm;

--
-- Name: auth_user_roles; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.auth_user_roles (
    user_id uuid NOT NULL,
    role_id uuid NOT NULL,
    assigned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assigned_by character varying(255)
);


ALTER TABLE public.auth_user_roles OWNER TO swm;

--
-- Name: auth_users; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.auth_users (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    created_by character varying(255),
    updated_by character varying(255),
    username character varying(128) NOT NULL,
    email character varying(320),
    display_name character varying(255),
    password_hash character varying(255) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    must_change_password boolean DEFAULT false NOT NULL,
    token_version integer DEFAULT 1 NOT NULL,
    last_login_at timestamp with time zone,
    last_login_ip character varying(64),
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE public.auth_users OWNER TO swm;

--
-- Name: device_events; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.device_events (
    id integer NOT NULL,
    device_id character varying(64) NOT NULL,
    ts timestamp with time zone NOT NULL,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    speed_kph double precision NOT NULL,
    heading integer NOT NULL,
    ignition boolean NOT NULL,
    attributes json NOT NULL
);


ALTER TABLE public.device_events OWNER TO swm;

--
-- Name: device_events_id_seq; Type: SEQUENCE; Schema: public; Owner: swm
--

CREATE SEQUENCE public.device_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.device_events_id_seq OWNER TO swm;

--
-- Name: device_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: swm
--

ALTER SEQUENCE public.device_events_id_seq OWNED BY public.device_events.id;


--
-- Name: device_vehicle_assignments; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.device_vehicle_assignments (
    device_id uuid NOT NULL,
    vehicle_id uuid NOT NULL,
    assigned_from timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assigned_to timestamp with time zone,
    active boolean DEFAULT true NOT NULL,
    remarks character varying(500),
    CONSTRAINT ck_dva_active_assigned_to CHECK (((active = false) OR (assigned_to IS NULL))),
    CONSTRAINT ck_dva_assigned_range CHECK (((assigned_to IS NULL) OR (assigned_to >= assigned_from)))
);


ALTER TABLE public.device_vehicle_assignments OWNER TO swm;

--
-- Name: devices; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.devices (
    id uuid NOT NULL,
    vendor_id uuid NOT NULL,
    imei character varying(17) NOT NULL,
    serial_no character varying(64),
    model character varying(128),
    manufacturer character varying(128),
    firmware_version character varying(64),
    sim_number character varying(32),
    installed_on timestamp with time zone,
    activated_on timestamp with time zone,
    last_seen timestamp with time zone,
    battery_percent double precision,
    signal_strength double precision,
    health_status character varying(16) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    metadata jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_devices_health_status CHECK (((health_status)::text = ANY ((ARRAY['healthy'::character varying, 'warning'::character varying, 'critical'::character varying, 'offline'::character varying])::text[])))
);


ALTER TABLE public.devices OWNER TO swm;

--
-- Name: drivers; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.drivers (
    id uuid NOT NULL,
    name character varying(255) NOT NULL,
    phone character varying(32),
    license_number character varying(64),
    license_expiry date,
    vendor_id uuid,
    assigned_vehicle_id uuid,
    active boolean DEFAULT true NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    person_type character varying(24) DEFAULT 'driver'::character varying NOT NULL,
    CONSTRAINT ck_drivers_person_type CHECK (((person_type)::text = ANY ((ARRAY['driver'::character varying, 'helper'::character varying, 'ic_member'::character varying])::text[])))
);


ALTER TABLE public.drivers OWNER TO swm;

--
-- Name: dump_yard_weighments; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.dump_yard_weighments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    assignment_id uuid,
    vehicle_id uuid NOT NULL,
    gtc_pickup_point_id uuid,
    dump_yard_id uuid NOT NULL,
    material_type character varying(32) NOT NULL,
    service_date date NOT NULL,
    entry_time timestamp with time zone NOT NULL,
    gross_weight_kg double precision DEFAULT '0'::double precision NOT NULL,
    tare_weight_kg double precision DEFAULT '0'::double precision NOT NULL,
    net_weight_kg double precision DEFAULT '0'::double precision NOT NULL,
    slip_number character varying(64),
    operator_name character varying(255),
    remarks character varying(1000),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.dump_yard_weighments OWNER TO swm;

--
-- Name: dump_yards; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.dump_yards (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    dump_yard_code character varying(32) NOT NULL,
    dump_yard_name character varying(255) NOT NULL,
    zone_id uuid,
    ward_id uuid,
    lat double precision,
    lng double precision,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    address character varying(1000),
    capacity double precision
);


ALTER TABLE public.dump_yards OWNER TO swm;

--
-- Name: geofences; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.geofences (
    id uuid NOT NULL,
    geofence_code character varying(32) NOT NULL,
    geofence_name character varying(255) NOT NULL,
    type character varying(16) NOT NULL,
    geometry_type character varying(16) NOT NULL,
    center_lat double precision,
    center_lng double precision,
    radius_meter double precision,
    polygon jsonb,
    ward_id uuid,
    active boolean DEFAULT true NOT NULL,
    scope_type character varying(16) DEFAULT 'ward'::character varying NOT NULL,
    scope_id uuid,
    geofence_for character varying(16) DEFAULT 'ward'::character varying NOT NULL,
    zone_id uuid,
    route_id uuid,
    CONSTRAINT ck_geofences_center_lat_range CHECK (((center_lat IS NULL) OR ((center_lat >= ('-90'::integer)::double precision) AND (center_lat <= (90)::double precision)))),
    CONSTRAINT ck_geofences_center_lng_range CHECK (((center_lng IS NULL) OR ((center_lng >= ('-180'::integer)::double precision) AND (center_lng <= (180)::double precision)))),
    CONSTRAINT ck_geofences_circle_fields CHECK ((((geometry_type)::text <> 'circle'::text) OR ((center_lat IS NOT NULL) AND (center_lng IS NOT NULL) AND (radius_meter IS NOT NULL) AND (polygon IS NULL)))),
    CONSTRAINT ck_geofences_geofence_for CHECK (((geofence_for)::text = ANY ((ARRAY['zone'::character varying, 'ward'::character varying, 'route'::character varying])::text[]))),
    CONSTRAINT ck_geofences_geometry_type CHECK (((geometry_type)::text = ANY ((ARRAY['circle'::character varying, 'polygon'::character varying])::text[]))),
    CONSTRAINT ck_geofences_polygon_fields CHECK ((((geometry_type)::text <> 'polygon'::text) OR ((polygon IS NOT NULL) AND (center_lat IS NULL) AND (center_lng IS NULL) AND (radius_meter IS NULL)))),
    CONSTRAINT ck_geofences_polygon_valid CHECK (((polygon IS NULL) OR public.st_isvalid(public.st_setsrid(public.st_geomfromgeojson((polygon)::text), 4326)))),
    CONSTRAINT ck_geofences_radius_positive CHECK (((radius_meter IS NULL) OR (radius_meter > (0)::double precision))),
    CONSTRAINT ck_geofences_scope_type CHECK (((scope_type)::text = ANY ((ARRAY['ward'::character varying, 'zone'::character varying])::text[]))),
    CONSTRAINT ck_geofences_type CHECK (((type)::text = ANY ((ARRAY['depot'::character varying, 'landfill'::character varying, 'zone'::character varying, 'parking'::character varying, 'maintenance'::character varying])::text[])))
);


ALTER TABLE public.geofences OWNER TO swm;

--
-- Name: gtc_checkpoints; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.gtc_checkpoints (
    id integer NOT NULL,
    truck_id character varying(128) NOT NULL,
    arrived_at timestamp with time zone NOT NULL,
    is_dry boolean DEFAULT false NOT NULL,
    is_wet boolean DEFAULT false NOT NULL,
    is_metal boolean DEFAULT false NOT NULL,
    is_plastic boolean DEFAULT false NOT NULL,
    is_sanitary boolean DEFAULT false NOT NULL,
    truck_cleanliness_score double precision,
    gtc_cleanliness_score double precision,
    remarks character varying(2000),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.gtc_checkpoints OWNER TO swm;

--
-- Name: gtc_checkpoints_id_seq; Type: SEQUENCE; Schema: public; Owner: swm
--

CREATE SEQUENCE public.gtc_checkpoints_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gtc_checkpoints_id_seq OWNER TO swm;

--
-- Name: gtc_checkpoints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: swm
--

ALTER SEQUENCE public.gtc_checkpoints_id_seq OWNED BY public.gtc_checkpoints.id;


--
-- Name: gts_points; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.gts_points (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    latitude double precision,
    longitude double precision,
    address character varying(1000),
    zone_id uuid,
    ward_id uuid,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.gts_points OWNER TO swm;

--
-- Name: operational_categories; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.operational_categories (
    id uuid NOT NULL,
    category_code character varying(32) NOT NULL,
    category_name character varying(255) NOT NULL,
    description character varying(1000),
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.operational_categories OWNER TO swm;

--
-- Name: pickup_point_crossings; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.pickup_point_crossings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_id character varying(128) NOT NULL,
    route_id uuid,
    pickup_point_id uuid NOT NULL,
    crossed_at timestamp with time zone NOT NULL,
    lat double precision NOT NULL,
    lng double precision NOT NULL,
    distance_m double precision NOT NULL,
    radius_m double precision NOT NULL,
    source character varying(32) DEFAULT 'telemetry'::character varying NOT NULL,
    imei character varying(17),
    vendor_id character varying(64),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.pickup_point_crossings OWNER TO swm;

--
-- Name: pickup_points; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.pickup_points (
    id uuid NOT NULL,
    pickup_name character varying(255) NOT NULL,
    ward_id uuid,
    route_id uuid,
    lat double precision,
    lng double precision,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    zone_id uuid,
    sequence_no integer DEFAULT 1 NOT NULL,
    pickup_radius_m double precision,
    expected_pickup_time character varying,
    is_gts boolean DEFAULT false NOT NULL,
    gts_id uuid
);


ALTER TABLE public.pickup_points OWNER TO swm;

--
-- Name: routes; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.routes (
    id uuid NOT NULL,
    route_name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    zone_id uuid NOT NULL,
    ward_id uuid NOT NULL,
    polyline_coordinates jsonb DEFAULT '[]'::jsonb NOT NULL,
    route_type character varying(24) DEFAULT 'primary'::character varying NOT NULL,
    CONSTRAINT ck_routes_route_type CHECK (((route_type)::text = ANY ((ARRAY['primary'::character varying, 'secondary'::character varying])::text[])))
);


ALTER TABLE public.routes OWNER TO swm;

--
-- Name: secondary_vehicle_assignments; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.secondary_vehicle_assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    vehicle_id uuid NOT NULL,
    gtc_pickup_point_id uuid NOT NULL,
    dump_yard_id uuid NOT NULL,
    material_type character varying(32) NOT NULL,
    assigned_from timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    assigned_to timestamp with time zone,
    active boolean DEFAULT true NOT NULL,
    remarks character varying(1000),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.secondary_vehicle_assignments OWNER TO swm;

--
-- Name: system_configurations; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.system_configurations (
    id uuid NOT NULL,
    config_key character varying(128) NOT NULL,
    config_type character varying(32) NOT NULL,
    description character varying(1000),
    value jsonb DEFAULT '{}'::jsonb NOT NULL,
    active boolean DEFAULT true NOT NULL,
    updated_by character varying(128),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_system_configurations_type CHECK (((config_type)::text = ANY ((ARRAY['speed_threshold'::character varying, 'geofence'::character varying, 'idle_threshold'::character varying, 'alert_rule'::character varying, 'webhook_secret'::character varying, 'vendor_config'::character varying, 'retention_policy'::character varying])::text[])))
);


ALTER TABLE public.system_configurations OWNER TO swm;

--
-- Name: ticket_comments; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.ticket_comments (
    id uuid NOT NULL,
    ticket_id uuid NOT NULL,
    author character varying(255),
    content character varying(4000) NOT NULL,
    is_internal boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.ticket_comments OWNER TO swm;

--
-- Name: tickets; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.tickets (
    id uuid NOT NULL,
    title character varying(255) NOT NULL,
    description character varying(4000),
    category character varying(32) DEFAULT 'complaint'::character varying NOT NULL,
    priority character varying(16) DEFAULT 'medium'::character varying NOT NULL,
    status character varying(16) DEFAULT 'open'::character varying NOT NULL,
    due_at timestamp with time zone,
    assigned_to character varying(255),
    created_by character varying(255),
    related_alert_id character varying(128),
    related_truck_id character varying(128),
    related_driver_id character varying(128),
    escalation_level integer DEFAULT 0 NOT NULL,
    sla_breached boolean DEFAULT false NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_tickets_category CHECK (((category)::text = ANY ((ARRAY['complaint'::character varying, 'maintenance'::character varying, 'driver_issue'::character varying, 'vehicle_issue'::character varying, 'route_issue'::character varying, 'pickup_issue'::character varying, 'other'::character varying])::text[]))),
    CONSTRAINT ck_tickets_escalation_non_negative CHECK ((escalation_level >= 0)),
    CONSTRAINT ck_tickets_priority CHECK (((priority)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT ck_tickets_status CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'in_progress'::character varying, 'pending'::character varying, 'resolved'::character varying, 'closed'::character varying])::text[])))
);


ALTER TABLE public.tickets OWNER TO swm;

--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.vehicles (
    id uuid NOT NULL,
    vehicle_number character varying(24) NOT NULL,
    registration_number character varying(24) NOT NULL,
    truck_type character varying(64),
    capacity_kg double precision NOT NULL,
    capacity_cubic_meter double precision NOT NULL,
    ward_id uuid NOT NULL,
    route_id uuid,
    fuel_type character varying(16) NOT NULL,
    operational_status character varying(16) NOT NULL,
    chassis_number character varying(64),
    engine_number character varying(64),
    manufacture_year integer,
    active boolean DEFAULT true NOT NULL,
    metadata jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    vendor_id uuid NOT NULL,
    vehicle_category character varying(16) DEFAULT 'primary'::character varying NOT NULL,
    secondary_waste_type character varying(32),
    CONSTRAINT ck_vehicles_capacity_cubic_meter_non_negative CHECK ((capacity_cubic_meter >= (0)::double precision)),
    CONSTRAINT ck_vehicles_capacity_kg_non_negative CHECK ((capacity_kg >= (0)::double precision)),
    CONSTRAINT ck_vehicles_fuel_type CHECK (((fuel_type)::text = ANY ((ARRAY['diesel'::character varying, 'petrol'::character varying, 'cng'::character varying, 'electric'::character varying, 'lng'::character varying])::text[]))),
    CONSTRAINT ck_vehicles_manufacture_year_range CHECK (((manufacture_year >= 1950) AND (manufacture_year <= 2100))),
    CONSTRAINT ck_vehicles_operational_status CHECK (((operational_status)::text = ANY ((ARRAY['operational'::character varying, 'maintenance'::character varying, 'breakdown'::character varying, 'retired'::character varying])::text[]))),
    CONSTRAINT ck_vehicles_secondary_waste_type CHECK (((secondary_waste_type IS NULL) OR ((secondary_waste_type)::text = ANY ((ARRAY['chicken_waste'::character varying, 'biomedical_waste'::character varying, 'construction_waste'::character varying, 'dry_waste'::character varying, 'green_waste'::character varying, 'mandai'::character varying, 'mix_waste'::character varying, 'mixed_waste'::character varying, 'plastic_waste'::character varying, 'wet_waste'::character varying])::text[])))),
    CONSTRAINT ck_vehicles_vehicle_category CHECK (((vehicle_category)::text = ANY ((ARRAY['primary'::character varying, 'secondary'::character varying])::text[])))
);


ALTER TABLE public.vehicles OWNER TO swm;

--
-- Name: vendors; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.vendors (
    id uuid NOT NULL,
    vendor_code character varying(32) NOT NULL,
    vendor_name character varying(255) NOT NULL,
    contact_person character varying(255),
    email character varying(320),
    phone character varying(32),
    webhook_secret character varying(255),
    signature_key character varying(255),
    allowed_ips jsonb NOT NULL,
    auth_type character varying(16) NOT NULL,
    callback_format jsonb NOT NULL,
    active boolean DEFAULT true NOT NULL,
    metadata jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT ck_vendors_auth_type CHECK (((auth_type)::text = ANY ((ARRAY['header'::character varying, 'signature'::character varying, 'ip'::character varying])::text[])))
);


ALTER TABLE public.vendors OWNER TO swm;

--
-- Name: wards; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.wards (
    id uuid NOT NULL,
    ward_name character varying(255) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ward_code character varying(24) NOT NULL,
    zone_id uuid NOT NULL,
    population integer,
    area double precision,
    total_pickup_points integer
);


ALTER TABLE public.wards OWNER TO swm;

--
-- Name: zones; Type: TABLE; Schema: public; Owner: swm
--

CREATE TABLE public.zones (
    id uuid NOT NULL,
    zone_code character varying(24) NOT NULL,
    zone_name character varying(255) NOT NULL,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    description character varying(512),
    supervisor_name character varying(255),
    supervisor_phone character varying(32)
);


ALTER TABLE public.zones OWNER TO swm;

--
-- Name: device_events id; Type: DEFAULT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.device_events ALTER COLUMN id SET DEFAULT nextval('public.device_events_id_seq'::regclass);


--
-- Name: gtc_checkpoints id; Type: DEFAULT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.gtc_checkpoints ALTER COLUMN id SET DEFAULT nextval('public.gtc_checkpoints_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.alembic_version (version_num) FROM stdin;
0030_ward_extra_fields
\.


--
-- Data for Name: alert_actions; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.alert_actions (id, alert_id, action_type, actor, notes, payload, created_at) FROM stdin;
cc255cc2-dd48-4bc4-8934-b1f8661f04d0	ba89035e-1d49-4464-829c-133bbbcc2dcf	escalated	ui	Escalated from Alerts page	{"status": "escalated", "escalation_status": "escalated"}	2026-06-01 12:32:48.248112+00
453ef3db-658c-4d01-a8bf-90c0b0ccac45	ba89035e-1d49-4464-829c-133bbbcc2dcf	escalated	ui	Escalated from Alerts page	{"status": "escalated", "escalation_status": "escalated"}	2026-06-01 12:32:51.808312+00
92623b26-8187-45fb-a32b-328f20ffec17	ec87a4d2-6b13-4f12-a47b-a862c0c80d06	escalated	ui	Escalated from Alerts page	{"status": "escalated", "escalation_status": "escalated"}	2026-06-01 12:33:20.6894+00
f5aabadb-d7a6-4424-a1c8-b80408c01ec6	7d6ff9fd-f0e4-4ad4-8816-593676f3cdc1	resolved	ui	Resolved from Alerts page	{"status": "resolved", "escalation_status": "none"}	2026-06-01 12:45:30.223053+00
\.


--
-- Data for Name: audit_logs; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.audit_logs (id, entity_type, entity_id, action, actor, before, after, metadata, created_at) FROM stdin;
\.


--
-- Data for Name: auth_permissions; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.auth_permissions (id, created_at, updated_at, deleted_at, created_by, updated_by, permission_key, permission_name, description, active) FROM stdin;
c81bcf4e-f611-45a1-bced-82d700a99579	2026-05-22 11:25:31.128938+00	2026-05-22 11:25:31.128938+00	\N	\N	\N	*	*	\N	t
\.


--
-- Data for Name: auth_role_permissions; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.auth_role_permissions (role_id, permission_id, assigned_at, assigned_by) FROM stdin;
a6fc520a-5235-400c-a7cc-3dc316ce1738	c81bcf4e-f611-45a1-bced-82d700a99579	2026-05-22 11:25:31.128938+00	\N
\.


--
-- Data for Name: auth_roles; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.auth_roles (id, created_at, updated_at, deleted_at, created_by, updated_by, role_key, role_name, description, active) FROM stdin;
a6fc520a-5235-400c-a7cc-3dc316ce1738	2026-05-22 11:25:31.128938+00	2026-05-22 11:25:31.128938+00	\N	\N	\N	admin	Admin	\N	t
\.


--
-- Data for Name: auth_user_roles; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.auth_user_roles (user_id, role_id, assigned_at, assigned_by) FROM stdin;
07e57aa8-b2eb-4d3e-898f-ca1388280cb1	a6fc520a-5235-400c-a7cc-3dc316ce1738	2026-05-22 11:25:31.128938+00	\N
\.


--
-- Data for Name: auth_users; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.auth_users (id, created_at, updated_at, deleted_at, created_by, updated_by, username, email, display_name, password_hash, active, must_change_password, token_version, last_login_at, last_login_ip, metadata) FROM stdin;
07e57aa8-b2eb-4d3e-898f-ca1388280cb1	2026-05-22 11:25:31.128938+00	2026-09-14 17:06:23.204306+00	\N	\N	\N	admin	\N	admin-user	pbkdf2_sha256$120000$gGgQhq5j8FSH169lCDwrEg$5oviEbgYZHJQQUU7R5HpMRF3rF5aCUVGmGHbIx2byFM	t	f	1	2026-09-14 17:06:23.267342+00	172.18.0.1	{}
\.


--
-- Data for Name: device_vehicle_assignments; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.device_vehicle_assignments (device_id, vehicle_id, assigned_from, assigned_to, active, remarks) FROM stdin;
54f2b816-dead-475d-b497-ef2035174088	72742592-59b8-4409-b9b6-eedd702ba23b	2026-09-14 12:29:13.783835+00	\N	t	\N
762a60c7-a647-44bd-aa35-7bd328a7a8c5	54b02dc0-f719-45c9-8a0d-b6e6e748acfd	2026-09-14 12:29:13.796849+00	\N	t	\N
d10ee69e-5518-438f-9e9d-b7519c129e05	1efc3e3f-cd86-4d33-9119-01037b52a7e7	2026-09-14 12:29:13.807792+00	\N	t	\N
ead0ed2b-72ee-4147-a824-80c86c8ed38a	1668dc55-77d2-432a-9880-0dc1e6e12093	2026-09-14 12:29:13.818312+00	\N	t	\N
ca5f7710-95d2-4684-a9ab-c085e6be2c20	4ea37df4-44a9-4cc1-9c87-190ca0212748	2026-09-14 12:29:13.828641+00	\N	t	\N
18fbaa41-4e7c-4b05-b141-259018e5ae77	12f47f2f-71e9-4b92-9144-8c3528b23b35	2026-09-14 12:29:13.839519+00	\N	t	\N
74f7252c-e54a-4ca1-82a7-0d53885916ff	10cc4968-5ab9-49b3-9593-91fb1d96db7f	2026-09-14 12:29:13.848645+00	\N	t	\N
c96f95cb-65d1-42e6-b3aa-e7a8a5db1d05	ef8fbf24-5944-49a1-a97b-fa47c522511f	2026-09-14 12:29:13.859548+00	\N	t	\N
fe657fa6-0e16-4d2c-b978-1ae277beb8ed	44ac0a5a-196b-4977-a678-f72e124636af	2026-09-14 12:29:13.870002+00	\N	t	\N
c96dc2a8-4e06-468e-9718-dacf74cbe032	74a3dd39-b709-4c75-8fb3-e7eef3b4b52b	2026-09-14 12:29:13.879696+00	\N	t	\N
8d66a4a0-5a55-42f4-89a4-12ffc6d738d7	802526ee-08fe-440f-9cec-2d940134471b	2026-09-14 12:29:13.890918+00	\N	t	\N
077c80fa-0b0b-42b2-aa6b-c65c103581fd	7c130b1b-f989-4c93-8c87-7a5ccddaae8c	2026-09-14 12:29:13.899323+00	\N	t	\N
1c943f6e-5f99-419a-97fa-102d7c51da6b	97b370c6-1cce-4cbd-82f0-d9a739d475df	2026-09-14 12:29:13.908285+00	\N	t	\N
dd41d1e9-bcd1-4a84-9f64-a3e209f7142c	0abf29e2-4772-4dc9-a0db-5b1ed139d89b	2026-09-14 12:29:13.916936+00	\N	t	\N
5f7fd298-0144-47e4-b8b6-024639c731cf	26282ab7-d30e-4480-a6e0-f4363376b47f	2026-09-14 12:29:13.926299+00	\N	t	\N
ff488a68-698b-4da1-baaa-24fea64da0ab	8fadfe4c-e423-42ae-ba7a-63f889b1802a	2026-09-14 12:29:13.935321+00	\N	t	\N
\.


--
-- Data for Name: devices; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.devices (id, vendor_id, imei, serial_no, model, manufacturer, firmware_version, sim_number, installed_on, activated_on, last_seen, battery_percent, signal_strength, health_status, active, metadata, created_at, updated_at) FROM stdin;
54f2b816-dead-475d-b497-ef2035174088	035536c7-c0b2-4427-8908-12e7a1fb36eb	866710035988523	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.545328+00	2026-09-14 12:29:13.545328+00
762a60c7-a647-44bd-aa35-7bd328a7a8c5	035536c7-c0b2-4427-8908-12e7a1fb36eb	866710035968897	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.564993+00	2026-09-14 12:29:13.564993+00
d10ee69e-5518-438f-9e9d-b7519c129e05	035536c7-c0b2-4427-8908-12e7a1fb36eb	868926034511946	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.580882+00	2026-09-14 12:29:13.580882+00
ead0ed2b-72ee-4147-a824-80c86c8ed38a	035536c7-c0b2-4427-8908-12e7a1fb36eb	868926034573599	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.597222+00	2026-09-14 12:29:13.597222+00
ca5f7710-95d2-4684-a9ab-c085e6be2c20	035536c7-c0b2-4427-8908-12e7a1fb36eb	356218600456170	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.613079+00	2026-09-14 12:29:13.613079+00
18fbaa41-4e7c-4b05-b141-259018e5ae77	035536c7-c0b2-4427-8908-12e7a1fb36eb	356218600956146	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.628382+00	2026-09-14 12:29:13.628382+00
74f7252c-e54a-4ca1-82a7-0d53885916ff	035536c7-c0b2-4427-8908-12e7a1fb36eb	357803370355055	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.642643+00	2026-09-14 12:29:13.642643+00
c96f95cb-65d1-42e6-b3aa-e7a8a5db1d05	035536c7-c0b2-4427-8908-12e7a1fb36eb	866330053247072	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.657626+00	2026-09-14 12:29:13.657626+00
fe657fa6-0e16-4d2c-b978-1ae277beb8ed	035536c7-c0b2-4427-8908-12e7a1fb36eb	356218601645482	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.671474+00	2026-09-14 12:29:13.671474+00
c96dc2a8-4e06-468e-9718-dacf74cbe032	035536c7-c0b2-4427-8908-12e7a1fb36eb	356218601961525	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.685629+00	2026-09-14 12:29:13.685629+00
8d66a4a0-5a55-42f4-89a4-12ffc6d738d7	035536c7-c0b2-4427-8908-12e7a1fb36eb	357803370392157	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.700542+00	2026-09-14 12:29:13.700542+00
077c80fa-0b0b-42b2-aa6b-c65c103581fd	035536c7-c0b2-4427-8908-12e7a1fb36eb	867111063124991	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.714959+00	2026-09-14 12:29:13.714959+00
1c943f6e-5f99-419a-97fa-102d7c51da6b	035536c7-c0b2-4427-8908-12e7a1fb36eb	867111063111626	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.729215+00	2026-09-14 12:29:13.729215+00
dd41d1e9-bcd1-4a84-9f64-a3e209f7142c	035536c7-c0b2-4427-8908-12e7a1fb36eb	357803370693901	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.743017+00	2026-09-14 12:29:13.743017+00
5f7fd298-0144-47e4-b8b6-024639c731cf	035536c7-c0b2-4427-8908-12e7a1fb36eb	867111062621948	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.757695+00	2026-09-14 12:29:13.757695+00
ff488a68-698b-4da1-baaa-24fea64da0ab	035536c7-c0b2-4427-8908-12e7a1fb36eb	357803373445671	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	healthy	t	{}	2026-09-14 12:29:13.771398+00	2026-09-14 12:29:13.771398+00
\.


--
-- Data for Name: drivers; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.drivers (id, name, phone, license_number, license_expiry, vendor_id, assigned_vehicle_id, active, metadata, created_at, updated_at, person_type) FROM stdin;
59e2bb5a-2432-4c3d-96e7-84d543eae48b	PARSHURAM FULE	\N	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	72742592-59b8-4409-b9b6-eedd702ba23b	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 12:29:13.946675+00	2026-09-14 12:29:13.946675+00	driver
e3a3eaf6-6b88-46ee-84e8-394b9b4e76f5	ANKUSH NALWADE	\N	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	54b02dc0-f719-45c9-8a0d-b6e6e748acfd	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 12:29:13.959192+00	2026-09-14 12:29:13.959192+00	driver
4341f8fb-ff0c-4a91-988b-30971bc514ff	SANI PAWAR	\N	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	1efc3e3f-cd86-4d33-9119-01037b52a7e7	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 12:29:13.97085+00	2026-09-14 12:29:13.97085+00	driver
bd4a6864-cad8-4ec8-bd6b-44d95df07352	RAJU DEVKER	9850259889	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	10cc4968-5ab9-49b3-9593-91fb1d96db7f	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.656926+00	2026-09-14 15:41:20.656926+00	driver
54dbf291-3265-46c7-9219-918ab685ebff	Unknown Driver-1	\N	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	ef8fbf24-5944-49a1-a97b-fa47c522511f	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.687341+00	2026-09-14 15:41:20.687341+00	driver
2b1177d5-8239-4619-a7bf-af76404d1191	SANJAY LONDHE	7387219244	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	26282ab7-d30e-4480-a6e0-f4363376b47f	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.704398+00	2026-09-14 15:41:20.704398+00	driver
6bdfa3ab-835a-4d90-a38b-26736d3cc9c1	HANUMANT KAMBLE	9145214599	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	8fadfe4c-e423-42ae-ba7a-63f889b1802a	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.726279+00	2026-09-14 15:41:20.726279+00	driver
7b257963-7ff7-4ffc-9b67-36bb05bd2c28	Unknown Driver -2	\N	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	97b370c6-1cce-4cbd-82f0-d9a739d475df	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.746929+00	2026-09-14 15:41:20.746929+00	driver
22e06304-22b3-4ed4-ad43-a53eed5823a7	HUSEN SHAIKH	9359892958	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	12f47f2f-71e9-4b92-9144-8c3528b23b35	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.757469+00	2026-09-14 15:41:20.757469+00	driver
fab82bc8-ea06-4f4a-b200-09a1f086cb46	Unknown Driver -4	\N	\N	\N	035536c7-c0b2-4427-8908-12e7a1fb36eb	74a3dd39-b709-4c75-8fb3-e7eef3b4b52b	t	{"email": null, "status": "active", "address": null, "join_date": null, "emergency_contact": null}	2026-09-14 15:41:20.767529+00	2026-09-14 15:41:20.767529+00	driver
\.


--
-- Data for Name: dump_yard_weighments; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.dump_yard_weighments (id, assignment_id, vehicle_id, gtc_pickup_point_id, dump_yard_id, material_type, service_date, entry_time, gross_weight_kg, tare_weight_kg, net_weight_kg, slip_number, operator_name, remarks, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: dump_yards; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.dump_yards (id, dump_yard_code, dump_yard_name, zone_id, ward_id, lat, lng, active, created_at, updated_at, address, capacity) FROM stdin;
\.


--
-- Data for Name: geofences; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.geofences (id, geofence_code, geofence_name, type, geometry_type, center_lat, center_lng, radius_meter, polygon, ward_id, active, scope_type, scope_id, geofence_for, zone_id, route_id) FROM stdin;
a7377245-69dd-476b-b401-8b5aa14858fa	ZONEF_BOUNDARY	Zone-F Boundary	zone	polygon	\N	\N	\N	{"type": "Polygon", "coordinates": [[[73.793488141349, 18.66062234687599], [73.78661174351697, 18.6640061342152], [73.78636785936263, 18.66391650934533], [73.78499917609764, 18.66305479297894], [73.78225307042095, 18.66234461336861], [73.78110278804837, 18.66181426149992], [73.77838190423218, 18.65993788203829], [73.77793794272347, 18.65939014963172], [73.7776321633448, 18.65923677903961], [73.77294715493896, 18.66425315125029], [73.77155789464548, 18.6657652605539], [73.77388313347356, 18.667582454455], [73.77629808390577, 18.67067115350171], [73.77771446023269, 18.67311758400357], [73.77832280660145, 18.67674585944402], [73.7788480068675, 18.67785753700383], [73.78015738193282, 18.68006038887852], [73.78131956126093, 18.68033868092522], [73.78187593844272, 18.68003518225489], [73.78313878196154, 18.68103267089851], [73.78397390670938, 18.68178281837856], [73.7845195558067, 18.68265646932973], [73.78666742526298, 18.68738616820936], [73.78850877572994, 18.69090990995238], [73.78805319209981, 18.69279047500335], [73.78759402600515, 18.69390527865451], [73.78667620822755, 18.69578000977564], [73.78659823834589, 18.69754941028464], [73.78729141128734, 18.69865690749464], [73.79023498705887, 18.70015793545246], [73.7964539815887, 18.70030702212741], [73.80113964691162, 18.7000060273379], [73.80708192045999, 18.6985300490175], [73.80744294154297, 18.69734467371295], [73.8082157993349, 18.69490529652369], [73.80845461697564, 18.69295405403347], [73.80880219656589, 18.69180228946043], [73.80888975466299, 18.6916241917345], [73.80937041001384, 18.69060890793125], [73.80941300363443, 18.69047680747862], [73.80991504668312, 18.69138705012231], [73.80994771341324, 18.69670356765647], [73.81050070152993, 18.69712079943189], [73.81261729534269, 18.69667927525315], [73.81421156848805, 18.69526335101717], [73.81393846523315, 18.69402531057746], [73.81393278240678, 18.69389276171667], [73.81353902534703, 18.69225697214003], [73.81313363790927, 18.69090574769997], [73.813692032352, 18.68994073308219], [73.81371388267583, 18.68984026298076], [73.81419990135872, 18.68866286440193], [73.81463405543685, 18.68804673968021], [73.81523420067485, 18.68696790111721], [73.81677816823704, 18.68598240040183], [73.81781304050138, 18.68536071385197], [73.8184543147165, 18.68488745615399], [73.81894127814547, 18.68409073480817], [73.81904771763375, 18.68339411194206], [73.81888732653057, 18.68270527338764], [73.81833746400012, 18.68200063795177], [73.81741061267346, 18.68111422088747], [73.81688703950076, 18.68062052132328], [73.81652514767084, 18.67973021234709], [73.8164352398221, 18.67733123805333], [73.81639664805725, 18.67530020032515], [73.81625186257037, 18.67449454567338], [73.81623046694807, 18.6740714583846], [73.81534485975615, 18.66637104124869], [73.81521319669694, 18.66497267959171], [73.81500852645569, 18.6636035453662], [73.81494287165086, 18.66306777377472], [73.81434382832377, 18.66255869248325], [73.81376515579957, 18.66224020330958], [73.8134475142583, 18.66182337586056], [73.81324820540252, 18.6609969110997], [73.81301265617904, 18.66026284127362], [73.81301340389146, 18.66023907514927], [73.81299896818757, 18.65920013624504], [73.81276910640027, 18.65861850232088], [73.81256782814559, 18.65797289809374], [73.81238511800983, 18.65753828260807], [73.80751977953409, 18.65906403210979], [73.80348919335151, 18.6604531146032], [73.8003401856943, 18.66184822088921], [73.79890141283589, 18.66282418176775], [73.79689114361226, 18.66363346571094], [73.79591138651, 18.66387750897323], [73.79519576924777, 18.66387369367866], [73.79443792793528, 18.66230467355285], [73.79375864787346, 18.66102725060079], [73.7936007862994, 18.66078076385591], [73.7935534956061, 18.66071076647933], [73.793488141349, 18.66062234687599]]]}	\N	t	zone	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	zone	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	\N
721c8aa3-6cf3-48c2-b4af-90fb28cf50be	F_W_11_BOUNDARY	F-W-11 Boundary	zone	polygon	\N	\N	\N	{"type": "Polygon", "coordinates": [[[73.80997701727217, 18.67899647429178], [73.81055731393582, 18.6786741441955], [73.81092808260554, 18.67852853990782], [73.81127010900467, 18.67848350431882], [73.8115273629847, 18.67847770885837], [73.81200290053543, 18.67854092391633], [73.81258809357642, 18.67876372063769], [73.81298533550759, 18.67898771679415], [73.81315095288473, 18.67913829630675], [73.81327701308936, 18.67926287188826], [73.81358226887562, 18.67935943523394], [73.81457743183088, 18.67905672525877], [73.81477084277509, 18.6788159255205], [73.81455242411863, 18.67689942709547], [73.81451971225368, 18.67648431860983], [73.81451181684321, 18.6762987750055], [73.8145296344743, 18.67619115117421], [73.81456090067734, 18.67612441197513], [73.81466091070125, 18.67594743895781], [73.81484517185555, 18.67557923638752], [73.81550017512998, 18.67417134592127], [73.81557011813642, 18.67399415072861], [73.81578823377511, 18.67394159702478], [73.81599280661341, 18.67390666249405], [73.81583810490952, 18.67219244685883], [73.81561434175435, 18.67087522313063], [73.81538710235543, 18.66950340515134], [73.81514561998115, 18.6679318632901], [73.81478877267135, 18.66577885506607], [73.8143018163845, 18.66336616149608], [73.81427669037441, 18.66321051017358], [73.81423186686926, 18.66313368163387], [73.81418201533585, 18.66299171698336], [73.81410952972627, 18.66288735637918], [73.81400139265061, 18.66274590830185], [73.81377123302975, 18.66270904841582], [73.81349626977406, 18.66271572911243], [73.81338448952229, 18.66273012808752], [73.81334842786028, 18.66263423946406], [73.81333528832003, 18.66255042996285], [73.81329600070282, 18.66243801109264], [73.81323636390586, 18.66236829063172], [73.81315555842637, 18.66227075799479], [73.81306442533008, 18.66217818273653], [73.81291704262199, 18.6619758500217], [73.81282651727183, 18.66172029721119], [73.81276562104505, 18.66148663516065], [73.8127037869468, 18.661246571739], [73.8126933379745, 18.66109335849858], [73.81251112311176, 18.65996871581277], [73.8124673728794, 18.65967073719794], [73.8124261046864, 18.65941316809009], [73.81222045746136, 18.65807215263596], [73.81218701440767, 18.65801059699014], [73.81214057697758, 18.65795639978483], [73.8112352404955, 18.65825006096694], [73.80932074580379, 18.65886326052627], [73.80762518845124, 18.65943662354148], [73.8075340935024, 18.65947034341547], [73.80747161729977, 18.65949608266454], [73.80758533108204, 18.66018578756502], [73.80770364873307, 18.66082874405095], [73.80776918225254, 18.6612213181312], [73.80781006810528, 18.66157097275079], [73.80785226030032, 18.66175566863883], [73.80791006158447, 18.66213955863411], [73.80804899789361, 18.66271975490303], [73.80685025708482, 18.66299600571413], [73.80673850132261, 18.66302614032416], [73.8067393161457, 18.66327017753026], [73.80614404146975, 18.66337811262873], [73.80496294644914, 18.66360373625506], [73.80460084497469, 18.66237899156978], [73.80433233635047, 18.66110392246475], [73.80435571614747, 18.66101783688501], [73.80500874584237, 18.66085651840535], [73.8050847826717, 18.66082920673299], [73.80506535436946, 18.66076224658297], [73.80505636919429, 18.66068463092078], [73.80459737357228, 18.66082299037504], [73.80456786983483, 18.66074818467684], [73.80450048674616, 18.66051553349533], [73.80444181130281, 18.6604646276982], [73.80335907401363, 18.66073832583704], [73.80326556027188, 18.66077652811347], [73.80328814490522, 18.66099747638569], [73.80341454747828, 18.66130207668687], [73.80377605780629, 18.66290843216141], [73.8042030292864, 18.66469848416648], [73.80426821392889, 18.66503825568846], [73.8017122376111, 18.66546833146002], [73.80157594466513, 18.66539556659847], [73.80104659506334, 18.66381221547494], [73.80098338787622, 18.66367460587689], [73.80078222018926, 18.66368505311655], [73.8004639551328, 18.66276146200166], [73.80044366049323, 18.66268941107234], [73.79859693602019, 18.66343730544522], [73.79849471204867, 18.66348101362501], [73.7985359162792, 18.66371113436712], [73.79550970351225, 18.66464715583745], [73.79545125732263, 18.66440215248995], [73.79536899541911, 18.66423028333924], [73.79525015440866, 18.66422884118257], [73.79510171158053, 18.66374753232407], [73.7950535574587, 18.66367398843553], [73.79300131886578, 18.66433856362167], [73.79290711196072, 18.66430215504107], [73.79286866501174, 18.66423468978936], [73.79282188177143, 18.66409355446574], [73.79280026934626, 18.66393610500583], [73.79204795791674, 18.661939966921], [73.79194582764475, 18.66181908983375], [73.79187899777897, 18.66167190123734], [73.79180120986597, 18.66163531540344], [73.7904654268744, 18.66237278076468], [73.78698712705858, 18.66408138132844], [73.7868156179606, 18.66418629090376], [73.78686288051688, 18.6643582962005], [73.7872180188022, 18.66437312071262], [73.7902672910147, 18.66279281591571], [73.79055562399148, 18.66334857104856], [73.79079855750474, 18.66423681889945], [73.78968811982418, 18.66488705381635], [73.78957811601629, 18.66518396435495], [73.78988932132081, 18.66549602828736], [73.79243706908387, 18.66429957948656], [73.79323172178395, 18.66665850089335], [73.79118785815422, 18.66677988852037], [73.79058543028675, 18.66693350570336], [73.7906618509848, 18.6685094982514], [73.78991963829588, 18.66863912379441], [73.78853846139877, 18.66848635398779], [73.78754182725872, 18.66850530897335], [73.78743888531584, 18.66891327928305], [73.78752807124356, 18.66915483456815], [73.78811506800201, 18.6692244184683], [73.78908067087545, 18.66944163534835], [73.78943260529329, 18.67070538694977], [73.78989018082109, 18.67094936517173], [73.79144388922374, 18.67049055187552], [73.79268224086334, 18.67008569683824], [73.7935626834215, 18.66999932257179], [73.79438053883183, 18.66997281522039], [73.7962232322703, 18.67018448197113], [73.79739931254646, 18.67036420570841], [73.79844182528149, 18.67064988791254], [73.79914440047186, 18.67106542560011], [73.80061828985272, 18.67245722092876], [73.80440025837575, 18.67489484670335], [73.80555090683772, 18.67550541228713], [73.80673036169527, 18.67626722648564], [73.8072522703259, 18.67645644678322], [73.80749325387372, 18.6766565876768], [73.80762084509644, 18.67732164648442], [73.80800011652207, 18.67760822750938], [73.80833082248422, 18.67760374247156], [73.80873160178182, 18.6779853750857], [73.8089807941656, 18.67841071358392], [73.80935244870342, 18.67882114606387], [73.80997701727217, 18.67899647429178]]]}	dcaaab0b-77f3-4766-9782-76814d1d4faa	t	ward	dcaaab0b-77f3-4766-9782-76814d1d4faa	ward	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	\N
\.


--
-- Data for Name: gtc_checkpoints; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.gtc_checkpoints (id, truck_id, arrived_at, is_dry, is_wet, is_metal, is_plastic, is_sanitary, truck_cleanliness_score, gtc_cleanliness_score, remarks, created_at) FROM stdin;
\.


--
-- Data for Name: gts_points; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.gts_points (id, name, latitude, longitude, address, zone_id, ward_id, active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: operational_categories; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.operational_categories (id, category_code, category_name, description, active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: pickup_point_crossings; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.pickup_point_crossings (id, vehicle_id, route_id, pickup_point_id, crossed_at, lat, lng, distance_m, radius_m, source, imei, vendor_id, created_at) FROM stdin;
\.


--
-- Data for Name: pickup_points; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.pickup_points (id, pickup_name, ward_id, route_id, lat, lng, created_at, updated_at, zone_id, sequence_no, pickup_radius_m, expected_pickup_time, is_gts, gts_id) FROM stdin;
e9a5d138-cd09-4a19-bf30-3e9bb3e535d2	MH-14-HG-6954 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66847494639631	73.79135781932123	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
362058f1-f65b-4c9d-b49c-e47ebf9bbac7	MH-14-HG-6954 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.6686243444267	73.78979830268041	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
666fe4b5-d485-4dbd-ba3e-a0af62b632e4	MH-14-HG-6954 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66813915210675	73.78911091796427	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
99bf4d72-64d1-445b-82cc-a625053b1228	MH-14-HG-6954 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66727973033845	73.78888142287936	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
6d768a13-673b-4dae-82d4-d8fea85f4fbc	MH-14-HG-6954 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66673505949968	73.7887785829772	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
5a98c0ed-4738-4612-8623-bd8e5e61bb43	MH-14-HG-6954 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66676626387567	73.7893814028588	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
8c367a60-4809-40a8-b569-228120f5eecf	MH-14-HG-6954 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66613790508196	73.79001003632105	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
6aa639a7-1473-430e-b7b8-06a3f16f5d45	MH-14-HG-6954 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66684425054649	73.78971132926407	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
a8a1f299-4853-4736-b454-f395d4647a3c	MH-14-HG-6954 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66730356874428	73.78927732193561	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
8d55e770-4b7f-4b27-96d3-a49bc2d17c5c	MH-14-HG-6954 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66790282055894	73.78979396156984	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
961273b3-13b3-40dd-a4c8-c96c641a6a4f	MH-14-HG-6954 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66768061096213	73.7916589911992	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
3507cc3e-0d61-4207-80e6-b0650e8233d8	MH-14-HG-6954 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66746076385986	73.79067849729111	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
1b6041c1-cc89-4326-958c-9c759bd95193	MH-14-HG-6954 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66695077753096	73.79094327983807	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
dbb63f99-eef1-4112-acaf-636667d600bd	MH-14-HG-6954 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66694441168255	73.79269659799773	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
075a9032-b6ee-4dfd-a4db-8b8db2a7048f	MH-14-HG-6954 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66563331889748	73.79331046357495	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
8217ed14-2eef-4c28-a7ec-70d41d5ccfe6	MH-14-HG-6954 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66551985281715	73.79409638551074	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
a4c408c1-4a00-4813-bf61-8326577ad8b4	MH-14-HG-6954 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66632049606453	73.79419807860904	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
39497d4e-4dd6-4d96-ba56-7e89fd17f529	MH-14-HG-6954 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66672531437229	73.79518223888174	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
129ffadd-b52b-475c-9fec-f5c1dbeeca55	MH-14-HG-6954 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66611449814453	73.79562366226209	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
3fcf9ec4-b39e-49e3-a263-1fc81f771289	MH-14-HG-6954 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	18.66502245959067	73.7939659882201	2026-09-14 16:06:33.212422+00	2026-09-14 16:06:33.212422+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
52123712-e476-406c-bf77-6af6cb274de4	MH-14-HG-6950 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66391156729845	73.80929723517401	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
75976c9a-5dc1-4c77-8522-4993ca8a1a1a	MH-14-HG-6950 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66263982028494	73.81330754256106	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
a8a386e5-4f9f-4978-afa7-c5e09275a4c9	MH-14-HG-6950 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66195219346701	73.8127911800949	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
336974c5-6a3d-4f1a-b442-6b2a3153575d	MH-14-HG-6950 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66270615269329	73.80990782133111	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
14569f60-602e-4b70-9c6b-d3568ec3b4ca	MH-14-HG-6950 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66417240724319	73.8084282710268	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
3f62c692-5c2a-4aed-8aeb-37e0f4743d0d	MH-14-HG-6950 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66386340686694	73.8069874109284	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
034f0a3b-24c3-4d6f-af52-72007c98790f	MH-14-HG-6950 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66286597575046	73.80753165340705	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
14253fcf-7f59-44d6-87f8-7f10527ad7f2	MH-14-HG-6950 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66148297016865	73.80794455014605	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
e0e12b48-e776-41ca-9e34-a12747e48f3a	MH-14-HG-6950 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66110814665782	73.81106820307738	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
a4f4b226-14fe-439d-a435-4c88f8c02b48	MH-14-HG-6950 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66179558310483	73.81159541309583	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
949d62d6-0410-42b7-990e-1b649653ac8c	MH-14-HG-6950 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.6613491289591	73.81257580782143	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
880d8159-901c-4782-ac89-37f52ca82875	MH-14-HG-6950 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.65969834388419	73.81158136542732	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
4a03db61-4b75-489f-a58e-f342c434e293	MH-14-HG-6950 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.65806524897279	73.81199971100759	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
815a8090-f912-4532-91b0-5ffca35d0441	MH-14-HG-6950 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.65909867583702	73.81085184898369	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
08288fee-1f14-49a3-a253-ee7e92a88495	MH-14-HG-6950 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.65989671791185	73.81027803631049	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
0d3b78c5-c643-4eaf-98ee-095b26126196	MH-14-HG-6950 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66031547296019	73.81123047589412	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
cec1f466-8982-4e78-b605-458b3a622ab2	MH-14-HG-6950 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66089884658531	73.81040575958221	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
4d5a8c45-7ebf-4e4d-a583-e4dad2bade9d	MH-14-HG-6749 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66473167390322	73.80702896981086	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
8fbddab0-3ed8-47f2-b2c1-3f1609550622	MH-14-HG-6749 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66335573358532	73.80682029846895	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
9961123f-4fad-42e9-be73-d2861e483d67	MH-14-HG-6749 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66341130520411	73.80630592831812	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
0b08be2e-ddfa-4bdf-b377-5efa2b4f3240	MH-14-HG-6749 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66398655542745	73.80640948650657	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
fad0e53a-ef19-4f86-97a9-4d148efb4dcc	MH-14-HG-6749 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66430170504808	73.80690463928805	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
bab45b30-33bd-4103-a75c-d62c2af8e7a9	MH-14-HG-6749 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66454500823197	73.80560779735778	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
e8d071d7-ece9-4a3b-a4fa-49c6a2d14ac0	MH-14-HG-6749 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66357922693301	73.80537218057975	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
24adf916-8a71-4ed0-958d-20f935851fa1	MH-14-HG-6749 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66368409147296	73.80489091108593	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
0af6c345-e57c-4410-9d8b-7b091f041b6b	MH-14-HG-6749 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66497289848231	73.80513322077547	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
c2220f8f-2bad-4dff-a077-f342460bbf2a	MH-14-HG-6749 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.6645695559103	73.80462768790616	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
ca4e556e-1d6e-4532-bac8-6ff5de1f5c2a	MH-14-HG-6749 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66405153714794	73.80410998500231	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
b6ab7254-1c36-46e8-8942-b7d0f191effa	MH-14-HG-6749 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66277204473139	73.8038240865147	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
d50b56ec-a1d0-4e40-876b-1af1c6daed06	MH-14-HG-6950 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66017610764927	73.80960941016255	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
5ab636b7-ea87-499c-9003-dd339b670e5b	MH-14-HG-6950 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.65839529029271	73.81096122307063	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
c511baca-fddf-47b5-843d-d4f4ec4f47d2	MH-14-HG-6950 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.65933071291885	73.80815364456768	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
e2729eaa-5964-4e76-88fe-472ef5eee02a	MH-14-HG-6950 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	18.66070963374904	73.80776777920643	2026-09-14 16:27:59.839434+00	2026-09-14 16:27:59.839434+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
6c0b5f6a-47b4-4b6e-8140-b6038d98bbf4	MH-14-JL-1325 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66615419493944	73.80393549058039	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
8946b47b-8b59-48e6-90c6-0a18256c259e	MH-14-JL-1325 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66658091892017	73.80398093744074	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
fe467a8e-137f-48e3-81a8-e22f62b9f8b8	MH-14-JL-1325 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66704163019785	73.80406995433631	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
c1beb624-7584-471c-8927-34bb8b741680	MH-14-JL-1325 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66753644376696	73.80417011183368	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
8bbccbb7-a753-483c-83f5-7b38bd088d3e	MH-14-JL-1325 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66751270044605	73.80482553305377	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
db9e3cfa-2390-4b8b-ba7a-cc1e9d139ef1	MH-14-JL-1325 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66710225589254	73.80474990852915	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
a32b3c7f-5681-460d-b380-5624625fef8b	MH-14-JL-1325 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66671290728015	73.80471214167038	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
37ffe2ff-09bc-4192-b31a-42213458930f	MH-14-JL-1325 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66651969654985	73.80500239779892	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
c23330f1-4380-415d-9d93-bc6ea5a21d62	MH-14-JL-1325 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66646470803191	73.80551262237495	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
5d6e56e4-3935-44bb-8085-fcf25efe43e8	MH-14-JL-1325 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66658401657389	73.80593488802101	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
9607f751-c5a3-43c4-91e0-3864b0158d4e	MH-14-JL-1325 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66709156321062	73.80602948051819	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
a29a7d6e-f8b5-4a9a-ab1d-075a80b8ae4e	MH-14-JL-1325 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66746378765572	73.80584681453217	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
089a2ba5-ed0a-477e-a676-6de52a015d55	MH-14-JL-1325 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66770351075384	73.80531624361491	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
59e89eb3-de84-46f2-956c-f6e4a7829e4c	MH-14-JL-1325 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.6679609493481	73.80459606637658	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
90e71d0a-331a-4262-bc06-564e10671bc6	MH-14-JL-1325 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66860165041023	73.80428118164384	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
12047bcd-9cd3-42f0-9430-c3a034007076	MH-14-JL-1325 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66890537453296	73.80430667782655	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
4a090c8f-fd20-43ab-a61c-4da82b4caa07	MH-14-JL-1325 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.6691892608648	73.80433815957765	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
f583e6fe-5db8-43d7-8612-cc5d9aff41da	MH-14-JL-1325 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66944821193286	73.80443384285458	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
c397da87-48e2-4fe4-a087-c217b7fb1932	MH-14-JL-1325 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66967182891538	73.80483453580648	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
e3809b54-2d44-4fe0-a577-6faf1f39a523	MH-14-JL-1325 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.6696270900816	73.80533243835109	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
349bbb2e-ae48-4594-b5c9-c3b66daa49ef	MH-14-JL-1325 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66958145533857	73.8058457622585	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
883f9551-3e9e-4f77-8ca6-8bda84706ec6	MH-14-JL-1325 Pickup 22	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66923348729837	73.80622742240078	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	22	\N	\N	f	\N
987e6942-8ef9-418b-9ad1-bd79ac269f83	MH-14-JL-1325 Pickup 23	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66889796556507	73.8058944936643	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	23	\N	\N	f	\N
39a8ae81-c57e-4d94-a1a6-7aef857bac10	MH-14-JL-1325 Pickup 24	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.6689746027139	73.80541278110204	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	24	\N	\N	f	\N
c742bb4a-2f70-4620-8470-9d091aca7e26	MH-14-JL-1325 Pickup 25	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66882227236851	73.80498393416119	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	25	\N	\N	f	\N
890c1cb7-635b-4646-b4dc-f45e09594982	MH-14-JL-1325 Pickup 26	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66832926779853	73.80492422661644	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	26	\N	\N	f	\N
3be87495-ded6-4231-ad17-35d41b0aa41a	MH-14-JL-1325 Pickup 27	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66796402753429	73.80490354630774	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	27	\N	\N	f	\N
68b8a699-41ca-4f52-9beb-8fa3f67cce7e	MH-14-JL-1325 Pickup 28	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66784780809036	73.80585726467399	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	28	\N	\N	f	\N
e854bc49-ae5f-49b5-b71a-b8804432e6b9	MH-14-JL-1325 Pickup 29	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66803932001718	73.80617533547772	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	29	\N	\N	f	\N
f27453e7-29a3-4c39-ad78-d420b8efcccd	MH-14-JL-1325 Pickup 30	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.66857848615953	73.80627032276216	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	30	\N	\N	f	\N
c21d51e7-0c3f-4c81-9a2c-90449eb03577	MH-14-JL-1325 Pickup 31	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	18.6690561634116	73.80649628930024	2026-09-14 16:28:00.494219+00	2026-09-14 16:28:00.494219+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	31	\N	\N	f	\N
1b297a32-7a3e-410d-a3c7-dc21c023c1a4	MH-14-HG-6749 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66182438106737	73.80379113389161	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
1dcf9382-2bb8-4194-8486-85df51c1c7da	MH-14-HG-6749 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66301091135217	73.80427329744957	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
d772347a-8c76-4941-a68a-e0419204a40b	MH-14-HG-6749 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66422192743012	73.8045441758235	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
7198b45e-3b08-4702-b29f-2dd3a014693f	MH-14-HG-6749 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66351512198984	73.80478525327787	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
be270703-c7de-4270-a955-e8038399148f	MH-14-HG-6749 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66181208909522	73.80439397759865	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
2b17234e-f370-49ae-92c6-fa4ae3c7cf98	MH-14-HG-6749 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66081276713111	73.80490431944204	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
e989b207-759a-432d-aff4-c5a1a26d1f9b	MH-14-HG-6749 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66051551195223	73.80447102208326	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
014ed9eb-5656-44e3-8868-df5cbabb66f3	MH-14-HG-6749 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66085035053647	73.80333665586265	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
dbfe2231-41c0-4dad-bf12-23dc87fa165a	MH-14-HG-6749 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66107548978689	73.80391871188586	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
4caad673-7d9c-42f1-8ffb-2b448af9619c	MH-14-HG-6749 Pickup 22	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.66160488191342	73.80354869783628	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	22	\N	\N	f	\N
77c54aa9-46d8-4317-b096-e7a7c62ea06a	MH-14-HG-6749 Pickup 23	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	18.6615116824409	73.80390879024037	2026-09-14 16:27:59.973896+00	2026-09-14 16:27:59.973896+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	23	\N	\N	f	\N
c496f706-7763-49b0-b463-f28173153d01	MH-14-HG-7113 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66354123028174	73.81245593795687	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
0299d678-44c1-4532-a3c6-236bff95bb39	MH-14-HG-7113 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66494383201406	73.8125476947346	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
6fe9c9de-ad32-4f6d-ac15-209e3ba7b8db	MH-14-HG-7113 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66598191260651	73.81260821001332	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
a59567d0-3009-42e8-8d05-eeb8f77a2e0c	MH-14-HG-7113 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66812218638334	73.81280977218067	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
4ba14a45-d895-4a02-a12a-52d32250825a	MH-14-HG-7113 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66609562457892	73.81284374938251	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
54154346-6737-4822-9dfc-dc2468c05ebc	MH-14-HG-7113 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66789085736615	73.81320998909237	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
ea8d9ce2-94c5-4951-811a-0fb251634125	MH-14-HG-7113 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66608659476112	73.81306788934094	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
46fa0e9e-7447-4a43-ba24-78ec5a836ca6	MH-14-HG-7113 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66802220947309	73.8136672923369	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
b52de605-72b4-495a-806c-e44a91cc44af	MH-14-HG-7113 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66482712196508	73.81321384805476	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
b0f69573-5fc8-40a8-b7ae-77c5038cfa68	MH-14-HG-7113 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66594587446398	73.81358933263834	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
bc656e24-0024-47bf-9dba-b217d7c0ec45	MH-14-HG-7113 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66479471156305	73.81350898202125	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
a8c4c282-5058-49a1-81af-6e8b4e26578c	MH-14-HG-7113 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66587409239161	73.81390351317641	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
9ee916a2-52a2-43c4-bd9b-0408a36589ee	MH-14-HG-7113 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66520318606869	73.8139295675438	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
e598a9f9-70ae-433f-ad68-7716e1268593	MH-14-HG-7113 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66570605542286	73.8145950814355	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
247a93ef-3416-42db-8e3a-1091927bb39f	MH-14-HG-7113 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66660114990064	73.81399661671013	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
45e5a84b-4407-4895-adbd-788c1b6e2ba6	MH-14-HG-7113 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66800535356848	73.81504490345857	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
8f4d357e-218b-4298-8c6a-5c2877553f69	MH-14-HG-7113 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66912760631701	73.81520793607868	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
3e3e7fa5-d82b-40fa-b529-a956fc25d2ec	MH-14-HG-7113 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.6689208366677	73.81405681395674	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
e9da0411-53f1-4ec0-99f0-ed58517cb5b0	MH-14-HG-7113 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66940700284426	73.81439515803939	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
e50938a7-6a20-4c6b-a223-76ae0d86c1b5	MH-14-HG-7113 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66980406263561	73.81398137412465	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
4dd39fe3-f646-4df2-bb04-62a754343105	MH-14-HG-7113 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66961611063008	73.81485846773344	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
a4d2e09c-f616-4393-92cf-1790498c9186	MH-14-HG-7113 Pickup 22	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.66981271216699	73.8153049917689	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	22	\N	\N	f	\N
c956ec85-5089-4b04-b36e-b88a5ee24f90	MH-14-HG-7113 Pickup 23	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67055844358635	73.8142389430131	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	23	\N	\N	f	\N
c11f8ee2-cf51-4c9e-b6e9-585a1200b99c	MH-14-HG-7113 Pickup 24	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67078974290167	73.81543446076978	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	24	\N	\N	f	\N
7a6fecad-7a26-442d-b4d3-8ab64104626f	MH-14-HG-7113 Pickup 25	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67129701732211	73.81465311961573	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	25	\N	\N	f	\N
be39f864-bc21-4026-aee1-2d3d540e3ce6	MH-14-HG-7113 Pickup 26	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67174679689666	73.81565106508855	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	26	\N	\N	f	\N
49595231-bce2-459a-a039-a9eced0e5e22	MH-14-HG-7113 Pickup 27	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67287072615131	73.81539779869046	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	27	\N	\N	f	\N
5f3c6025-e6a8-4589-b6bd-fe65877be924	MH-14-HG-7113 Pickup 28	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67354064055205	73.81584264363076	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	28	\N	\N	f	\N
464e49c9-9acb-4831-b04c-9b8e613f76a0	MH-14-HG-7113 Pickup 29	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67522089870704	73.81484497842686	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	29	\N	\N	f	\N
65d20da9-deb9-4f8b-945b-7ad56d097e99	MH-14-HG-7113 Pickup 30	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67674262599408	73.81323136409688	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	30	\N	\N	f	\N
496bbefd-5755-455b-be64-5a5143a811f6	MH-14-HG-7113 Pickup 31	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	18.67755321913245	73.81444058762632	2026-09-14 16:28:00.063606+00	2026-09-14 16:28:00.063606+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	31	\N	\N	f	\N
029154f3-1829-433b-a1cf-73df2d0c662f	MH-14-KA-2275 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66372882610609	73.7949580844514	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
14d1ada2-971d-4319-9f5c-8cb08ab00e76	MH-14-KA-2275 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66410278566248	73.79383907166873	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
92a5c5b2-d35c-4560-956e-730e5e77dd74	MH-14-KA-2275 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66440381865484	73.79289170406008	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
46efd416-a1ff-42d3-a319-5d6c4821157a	MH-14-KA-2275 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66383397112715	73.79267513853434	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
38e03337-01bf-4723-b665-2e3f8be6a8df	MH-14-KA-2275 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66436211204071	73.79107356330665	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
46e14000-0e33-4ef1-87d1-4e7c3175b8c4	MH-14-KA-2275 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66504022616408	73.79008384048942	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
62fd58cb-75e7-4b93-9d68-c936e58b06a4	MH-14-KA-2275 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.664501301846	73.7893692652608	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
f2355881-ca37-41b7-b72f-c04988782535	MH-14-KA-2275 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66355406552007	73.78830469604657	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
99be7ab7-04e7-4742-9099-798703c14e22	MH-14-KA-2275 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66288893600547	73.78964896247712	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
3d179d4b-db4a-4faf-ab70-5980686c3d06	MH-14-KA-2275 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.6622517121405	73.79077346976013	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
7d7496a5-ef5a-4fe4-b195-48d5e8aacd17	MH-14-KA-2275 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66320654610036	73.7911236472563	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
fcf79504-9371-4a3f-94c4-949a1c1dcfe3	MH-14-KA-2275 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66395453098602	73.79139695157257	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
d17754b5-9367-4aae-a139-5d7e32b5bc35	MH-14-KA-2275 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66359761346504	73.79258826630566	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
42e6ccc9-efd8-4544-bef4-49bdb9033b40	MH-14-KA-2275 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66264577962604	73.79218201080089	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
90aed074-875d-40a9-8409-5f293254d834	MH-14-KA-2275 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	18.66171798991135	73.7917676004643	2026-09-14 16:28:00.155948+00	2026-09-14 16:28:00.155948+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
2d6462be-0101-456c-baf9-3584d3622ac5	MH-11-M-4303 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66710395504652	73.80605988839525	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
3536f72c-f470-4a0e-b893-c6a7600eb9e4	MH-11-M-4303 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.6674723606691	73.80643961386255	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
766e7422-59fc-4539-8142-a83e29979476	MH-11-M-4303 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66749270668126	73.80686429378187	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
ed2f8641-3769-41ea-9cc6-019aa689bf49	MH-11-M-4303 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66722233007541	73.80731698503587	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
b54899ca-dd1b-462b-8b1f-d64e028be892	MH-11-M-4303 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.6668288961773	73.80729133552308	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
7fcd66b5-4fcc-40ae-8fd2-a9d114ad7ce8	MH-11-M-4303 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66636583359764	73.80677963811755	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
2f8d7bf1-2cd1-44ff-9ab1-67357d6ef385	MH-11-M-4303 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66639984053728	73.8063107431964	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
3a794487-1c19-4929-8297-7f69642d7a46	MH-11-M-4303 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66568235976616	73.80779151567873	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
911477e0-e697-409f-8a37-98f194ddab1b	MH-11-M-4303 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66599222948089	73.8078324917199	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
ead4a317-99bb-4f4b-8a2a-9dae21acd4db	MH-11-M-4303 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66626798098821	73.80785896408105	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
7a123956-3d50-4811-893f-333499b951f9	MH-11-M-4303 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66653438939709	73.80793595901832	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
902b88e8-4f1a-494e-95fc-1861a85d1330	MH-11-M-4303 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66679951444987	73.80796930419342	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
3147b30e-52d2-4a1c-8798-cbfb881b3a21	MH-11-M-4303 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66713934254873	73.80802887188574	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
c8069b24-5f58-4eaf-9eae-af27ece600bd	MH-11-M-4303 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66768916742094	73.80652882697848	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
7f0e1f45-39c4-45d3-8264-511cb4ea68ee	MH-11-M-4303 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66805672293381	73.8062715937389	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
133c12bd-29b1-4aa3-97ac-d643df2d1758	MH-11-M-4303 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66837448758294	73.80632169847976	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
a5fa5136-a002-4cbb-8184-4f3001133eb8	MH-11-M-4303 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66872742469814	73.80637363931186	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
a5122a2d-9c84-4afd-9fbc-e50a366d2e0b	MH-11-M-4303 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66876657672751	73.80687495042751	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
5e8c3b16-36de-426d-a1da-7fdb754e6469	MH-11-M-4303 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66872483024325	73.80721430717335	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
60c37723-91ad-44f9-990d-fad65ea90512	MH-11-M-4303 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.6682097856079	73.80749494020989	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
eae99905-e65b-41e3-b57c-bb22f50be29a	MH-11-M-4303 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66793758631663	73.80746405929855	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
f40733b5-dbe1-411a-8626-6820911ef49c	MH-11-M-4303 Pickup 22	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66765267614282	73.80742723454817	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	22	\N	\N	f	\N
01432be5-c31e-4e0c-8af8-6b6b2054f5f6	MH-11-M-4303 Pickup 23	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66753281154142	73.80786710501641	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	23	\N	\N	f	\N
25df0f65-47a0-4b7a-897e-1580add9a780	MH-11-M-4303 Pickup 24	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.6679016246755	73.80811508854146	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	24	\N	\N	f	\N
f0b3f676-bbee-455a-bdfd-e8aa511d587f	MH-11-M-4303 Pickup 25	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66824309628113	73.80816815982617	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	25	\N	\N	f	\N
77c1f679-a430-4b97-acca-365116004121	MH-11-M-4303 Pickup 26	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66847093175783	73.80822902133248	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	26	\N	\N	f	\N
c3ceb548-ce1c-4b1f-8a43-d52c96bf1427	MH-11-M-4303 Pickup 27	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66874297388237	73.80827551108686	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	27	\N	\N	f	\N
65fee42e-b563-4f36-8eaa-15c278a08582	MH-11-M-4303 Pickup 28	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66904815878375	73.80830253986178	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	28	\N	\N	f	\N
a8e54d15-05c1-47fc-bfd8-9c2914a10f96	MH-11-M-4303 Pickup 29	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66925988933202	73.80788630130965	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	29	\N	\N	f	\N
be32d7c0-1f51-4e31-a2d5-ff087ccff795	MH-11-M-4303 Pickup 30	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66935457201551	73.80726216284143	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	30	\N	\N	f	\N
adcc1d9c-a3f0-4529-81e2-b6a541adc55d	MH-11-M-4303 Pickup 31	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.6694332688475	73.80671193633569	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	31	\N	\N	f	\N
83793f0c-ed3d-4e76-89d9-567e7a1c0eab	MH-11-M-4303 Pickup 32	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	18.66921073992538	73.80651542081797	2026-09-14 16:28:00.228539+00	2026-09-14 16:28:00.228539+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	32	\N	\N	f	\N
2d596ed8-e1cd-498f-9838-f992ad13057c	MH-14-KA-2273 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66998469465461	73.80464357744485	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
10d09f7b-8835-4595-ac3d-1bfe5a25d3c7	MH-14-KA-2273 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67058669829329	73.80479005950431	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
fc2475ab-6c06-4b88-99e5-d5e259778960	MH-14-KA-2273 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67098264976283	73.80489427157983	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
0eaef984-50e9-49aa-a7ef-78d6ded7430a	MH-14-KA-2273 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67108373094934	73.8051412740255	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
87bba08d-7b51-46f5-b81d-edea8467311e	MH-14-KA-2273 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67069803209126	73.80505065361119	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
0e2f4640-7298-4f20-92c9-cad4ae9e9fe9	MH-14-KA-2273 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67043577227695	73.80520537609834	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
992a089a-93df-4e11-b25e-c73b4fe0144f	MH-14-KA-2273 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67065996343937	73.80525528325565	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
49e351b3-37cf-458e-b004-b0be6a9485c4	MH-14-KA-2273 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67102518032218	73.80534612796589	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
dcc0b600-3e32-45fc-b9a5-c85a7d1c70e2	MH-14-KA-2273 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67078011222934	73.80630065969598	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
dcb809c1-bdac-42a7-876f-f30e062cd71f	MH-14-KA-2273 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66974233573733	73.80618008950096	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
27622b5e-8280-4ef5-8ab9-a8595a521a2d	MH-14-KA-2273 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66407162114146	73.81157327364372	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
4551618d-896b-4140-8a12-fff3ad9b53ae	MH-14-KA-2273 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.6644610099598	73.81107459252024	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
231de752-8e3f-4b15-a4f3-8e116c9969e4	MH-14-KA-2273 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.6658033488751	73.80803593888011	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
250a7d55-2070-4ea0-a1fb-df4832add0ce	MH-14-KA-2273 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66643331739881	73.80821502406083	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
920c494e-c87e-4e76-89d8-8523c817319a	MH-14-KA-2273 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66732099959033	73.80842597841279	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
fefd2e65-ce7e-4752-8b73-f04f73018e6b	MH-14-KA-2273 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66810895603469	73.80858604450925	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
4eadb77a-0a50-457f-b701-7b8015dd2945	MH-14-KA-2273 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66895528256043	73.80877344093066	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
cc3d7b7b-dc5f-4740-85a7-5710fd5d747c	MH-14-KA-2273 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67015401045815	73.80909350265841	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
4c2ccd16-025a-4d91-a7a9-28666c3ed9c9	MH-14-KA-2273 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.67133662174434	73.80929757206056	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
ee50d619-c033-4507-a05b-0dec763d4087	MH-14-KA-2273 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66597092256042	73.80873843023656	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
c94fc42e-f525-4707-aef4-a07bcaff5bdc	MH-14-KA-2273 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.6663932930251	73.80932309224968	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
f393f1df-e65d-4058-9ff2-651c8de77f89	MH-14-KA-2273 Pickup 22	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66578442981996	73.80956244712578	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	22	\N	\N	f	\N
905091ab-a53b-4c01-ba9b-bc53055c5b65	MH-14-KA-2273 Pickup 23	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.6656444021581	73.80999020854509	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	23	\N	\N	f	\N
21559dd4-d993-44e6-a0eb-6cfa48803d4c	MH-14-KA-2273 Pickup 24	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66574416266627	73.81036833614631	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	24	\N	\N	f	\N
eed74055-424d-4a4a-afad-71b769f736de	MH-14-KA-2273 Pickup 25	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66616317873181	73.8107715262296	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	25	\N	\N	f	\N
620303b6-0e1d-4882-acdb-99542b3a31a2	MH-14-KA-2273 Pickup 26	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66752774250313	73.81093648915837	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	26	\N	\N	f	\N
3336bc88-72de-4b00-8d25-1e526b419af2	MH-14-KA-2273 Pickup 27	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66819617807527	73.81100812002082	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	27	\N	\N	f	\N
fa871215-3cad-405e-8622-a8f20ca0f78f	MH-14-KA-2273 Pickup 28	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66907223217207	73.81111825530868	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	28	\N	\N	f	\N
b373998a-099a-404f-9656-b754632f5229	MH-14-KA-2273 Pickup 29	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66560109138275	73.81092562520294	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	29	\N	\N	f	\N
01f38136-237f-484c-8432-bb42c6c9e36e	MH-14-KA-2273 Pickup 30	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	18.66530495319126	73.80912905049904	2026-09-14 16:28:00.352333+00	2026-09-14 16:28:00.352333+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	30	\N	\N	f	\N
4f4cd1a7-0204-4ce2-b79a-8cd85f31232e	MH-14-HG-7121 Pickup 1	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67471234648005	73.8047022466768	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	1	\N	\N	f	\N
7fe50eae-80f8-49dc-b967-2d6413e92ae4	MH-14-HG-7121 Pickup 2	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67532946331421	73.8056589083686	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	2	\N	\N	f	\N
1ffc1a1c-5190-4330-ad50-4adb137dcbb6	MH-14-HG-7121 Pickup 3	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67576064429061	73.80660869642394	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	3	\N	\N	f	\N
fc901b74-dc09-423b-ad05-7b788634cb72	MH-14-HG-7121 Pickup 4	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.6770550144656	73.80779035511665	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	4	\N	\N	f	\N
2e6151c7-e6f2-4f16-99c4-5aca5c7f5679	MH-14-HG-7121 Pickup 5	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67776320498825	73.80903048923663	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	5	\N	\N	f	\N
59bf5199-3742-47d7-bdad-35db5023878e	MH-14-HG-7121 Pickup 6	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67833259650494	73.80926294736527	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	6	\N	\N	f	\N
4a424494-c282-41f5-a826-caadc4c9b4cb	MH-14-HG-7121 Pickup 7	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67862756953539	73.80977248822711	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	7	\N	\N	f	\N
0ad55bc4-c7b1-4840-aafd-53d022964292	MH-14-HG-7121 Pickup 8	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67536405624318	73.80719169773118	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	8	\N	\N	f	\N
f6ee97d3-9ffb-407c-966e-ef2b858d17e1	MH-14-HG-7121 Pickup 9	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.674577178793	73.80711758833344	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	9	\N	\N	f	\N
60176e9e-8fec-460b-acdd-6c43e816af40	MH-14-HG-7121 Pickup 10	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67440614544456	73.80799668144265	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	10	\N	\N	f	\N
1bd75509-ad4c-4da3-bc0a-b436b2d1860d	MH-14-HG-7121 Pickup 11	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67402145007094	73.8096150719124	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	11	\N	\N	f	\N
03d3848b-a272-489a-807a-330d73086c8b	MH-14-HG-7121 Pickup 12	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67416671057657	73.80902240831647	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	12	\N	\N	f	\N
509a47e5-ff11-4ef4-823c-ce625fb0a157	MH-14-HG-7121 Pickup 13	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67455623993882	73.81027763820303	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	13	\N	\N	f	\N
d4f899db-3a17-4cea-830e-812696d6e6e0	MH-14-HG-7121 Pickup 14	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67587556410578	73.8107499650762	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	14	\N	\N	f	\N
19ca8d98-5df9-4b15-b625-97892b7ed7e1	MH-14-HG-7121 Pickup 15	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67798619014801	73.81127612276642	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	15	\N	\N	f	\N
601d8c08-483f-4327-9dcc-0ca236ba5641	MH-14-HG-7121 Pickup 16	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67334579442321	73.80969639910755	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	16	\N	\N	f	\N
efb47fe2-37a5-4e9f-a951-0ab490070728	MH-14-HG-7121 Pickup 17	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67268008500685	73.80954604816661	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	17	\N	\N	f	\N
5eee6b56-5281-4fdf-83ce-8e932f21965e	MH-14-HG-7121 Pickup 18	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67196655239942	73.80946310015807	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	18	\N	\N	f	\N
00dfb523-c1a2-40a1-84c5-051d5dc58655	MH-14-HG-7121 Pickup 19	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67194435574297	73.8081554838916	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	19	\N	\N	f	\N
227ed23a-5605-4e78-8f01-b46b1e2ebf4a	MH-14-HG-7121 Pickup 20	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67209652826118	73.80706734481981	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	20	\N	\N	f	\N
a5ba67a5-2ceb-4ab7-97d2-88d6faa1bc75	MH-14-HG-7121 Pickup 21	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67239953283821	73.80654844802461	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	21	\N	\N	f	\N
9d5c8c2b-1bfc-4717-86e6-5d8a6ca4f602	MH-14-HG-7121 Pickup 22	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67284385434585	73.8066145894251	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	22	\N	\N	f	\N
450855ca-1014-4448-ac6b-f2b0e617be18	MH-14-HG-7121 Pickup 23	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67346209721713	73.80716531386851	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	23	\N	\N	f	\N
24010314-25fc-4b6f-a452-5822f2d75a70	MH-14-HG-7121 Pickup 24	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67193770262529	73.80647720100801	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	24	\N	\N	f	\N
f4a899a2-7dbe-4d1f-aa62-1daf1e8cb9f5	MH-14-HG-7121 Pickup 25	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67136843190554	73.80643682682735	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	25	\N	\N	f	\N
6875dad0-84f1-49f2-a4b2-0a851a1fe9d3	MH-14-HG-7121 Pickup 26	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	18.67332909494196	73.80513984831099	2026-09-14 16:28:00.433678+00	2026-09-14 16:28:00.433678+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	26	\N	\N	f	\N
\.


--
-- Data for Name: routes; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.routes (id, route_name, created_at, updated_at, zone_id, ward_id, polyline_coordinates, route_type) FROM stdin;
17c994ed-d970-46e1-a4af-26152eaa8b8b	F11 Route - MH-14-HG-6954	2026-09-14 15:53:32.79901+00	2026-09-14 15:53:32.79901+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.79136102414459, 18.66850585141679], [73.79114851012052, 18.66855472491237], [73.79081619213181, 18.66860602597491], [73.79061813374256, 18.66862475284797], [73.7898127638449, 18.66865890942221], [73.78983762305795, 18.66832823527321], [73.78983889819426, 18.66825960823332], [73.7892588233611, 18.66822665215667], [73.78919324409702, 18.66820358856083], [73.78910674461007, 18.66813662862484], [73.78894080556744, 18.66736733981605], [73.78891680503578, 18.66728351365679], [73.7888166136523, 18.66727618181097], [73.7887655623211, 18.66728855003633], [73.78872124310817, 18.66729439014892], [73.78871140378031, 18.66725576135895], [73.7887598723136, 18.66679128782899], [73.78878816918184, 18.66673500071007], [73.78910969815186, 18.6667570818461], [73.78928285222658, 18.66678056309766], [73.78936646045857, 18.66680201472634], [73.78940966230415, 18.66671335427124], [73.78944926818721, 18.66661436104697], [73.7894851765242, 18.66650884402162], [73.78956360458797, 18.66641211199309], [73.7896689144373, 18.66629844922219], [73.78981730905508, 18.66620510118769], [73.78990278289048, 18.66615760802784], [73.78996930091445, 18.66614179502793], [73.79002457809946, 18.66613118386434], [73.7903701102384, 18.66687193579308], [73.7903753679169, 18.66689296266841], [73.7903465353719, 18.66691067159596], [73.78947780882928, 18.66679081416737], [73.7894649991706, 18.66685009736542], [73.79031520832982, 18.66695460935736], [73.79035076982088, 18.66695983872494], [73.79030879127374, 18.66737149741899], [73.78907362924987, 18.6672516889242], [73.78899295985647, 18.66726006587403], [73.78899413272431, 18.66730345850375], [73.78982972957088, 18.66742765817505], [73.78980152734397, 18.66810694278814], [73.7898161475724, 18.66816193749818], [73.7909643656433, 18.66803274055313], [73.79128841411901, 18.66799887123935], [73.79171673414493, 18.66796705047499], [73.7916284759157, 18.66747907048208], [73.79047437887249, 18.66746701363422], [73.79038356958168, 18.66746690635163], [73.7903208096344, 18.66744899903815], [73.79038921957427, 18.66695351658454], [73.79122812913711, 18.66696226384224], [73.79150610996638, 18.66696691144205], [73.79275244827028, 18.66697197466948], [73.79316809440753, 18.66694638410407], [73.79345666463507, 18.66693929548869], [73.79370599195342, 18.66694431485324], [73.79339643524506, 18.6659022807278], [73.79318192694866, 18.66517218092002], [73.79318118443983, 18.66511340874017], [73.79366840018893, 18.66507547710962], [73.79372883567265, 18.66524551013258], [73.79380014720734, 18.66557518494405], [73.79394977164124, 18.66557157371075], [73.79438117019431, 18.66546067813098], [73.79486136718424, 18.66537624581895], [73.79497700404416, 18.66585442153471], [73.79498738564945, 18.66592205174194], [73.79450647950574, 18.66604214504846], [73.79440071082297, 18.66608570020893], [73.79428166864793, 18.66619041573141], [73.79407435667783, 18.66652557177543], [73.7941529446886, 18.66672415019724], [73.79507638922884, 18.6664083324237], [73.79530905902233, 18.66712471131963], [73.79592451937756, 18.66691703893596], [73.79584594349387, 18.66673668935975], [73.79550779591031, 18.66578067623653], [73.79541802968586, 18.6652875680686], [73.79531896336188, 18.66488566597651], [73.79530000200299, 18.66476317965761], [73.79475826842386, 18.66489287100478], [73.793826628438, 18.66505711560501]]	primary
5b2a6017-c8ba-47a5-a41c-62d9843ad666	F11 Route - MH-14-HG-6950	2026-09-14 16:27:59.746402+00	2026-09-14 16:27:59.746402+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.80928265259497, 18.66394939162746], [73.8109943394507, 18.66335976037441], [73.81145540058083, 18.66320409705942], [73.81233467300352, 18.66293928574616], [73.8130733067826, 18.66281027936013], [73.81329112520525, 18.66274531196634], [73.81331950426741, 18.66262916227341], [73.81321915818417, 18.66243442161726], [73.8128052245898, 18.66210252210475], [73.81268838008157, 18.66203370698054], [73.81252943043751, 18.66199908304648], [73.8083543033457, 18.66319618601707], [73.80829240011272, 18.6632141492879], [73.80825624992366, 18.66327946374181], [73.8082892640428, 18.66348718356737], [73.80845328688744, 18.6642231310197], [73.80716239395106, 18.66474778190524], [73.80697973265664, 18.66384890568791], [73.8068299997109, 18.66302783313531], [73.80803367380634, 18.66281079912859], [73.80813063813551, 18.66278984316434], [73.8080798029901, 18.66263107995977], [73.80788622137446, 18.66156208043793], [73.80793523513843, 18.66148454536557], [73.80969180311477, 18.66127287866884], [73.81121458652305, 18.66111124970386], [73.81148942442239, 18.66109962993141], [73.81152475633166, 18.66113290034751], [73.81153548610274, 18.66120393166617], [73.81165436057958, 18.662151439583], [73.81167108360967, 18.6622032326617], [73.81257717425753, 18.66195550218379], [73.81271732026323, 18.66190465896617], [73.81273586155702, 18.66186207098932], [73.81260313290788, 18.66161311662775], [73.81258559312026, 18.66142200430762], [73.81252478490788, 18.6610544678396], [73.81246006666255, 18.66098390491475], [73.812285549039, 18.66098251264341], [73.81172025109193, 18.66100255225277], [73.81148257882785, 18.65896857200551], [73.81142142391434, 18.65839046108917], [73.81145011165559, 18.65829910041589], [73.81214402838717, 18.65805118534507], [73.81211568828806, 18.65802244239959], [73.81197526612853, 18.65806039862064], [73.81134615506856, 18.65826382088451], [73.81138224645909, 18.65843624026597], [73.81143583682255, 18.65892360545974], [73.8113189444237, 18.65893954194472], [73.81025678228265, 18.6593344383079], [73.81021079714503, 18.65941851360838], [73.81031305999785, 18.66021491798421], [73.81037231965566, 18.66023728374097], [73.81109769706077, 18.66017343643228], [73.81121045516633, 18.66024626714714], [73.81124952153253, 18.66037710603169], [73.81125616622401, 18.66044458685003], [73.81047153770766, 18.66054479065488], [73.81036719926186, 18.66059681264379], [73.81041863927706, 18.66114141318008], [73.81037158440358, 18.66116859332123], [73.80975604547876, 18.66124160647238], [73.8097186244938, 18.66122210944116], [73.80970306764912, 18.6610403778739], [73.80958294916596, 18.66009681128063], [73.80945864912047, 18.65917227515197], [73.80944689279761, 18.65901642743547], [73.80947869834115, 18.65894816203539], [73.8112410062447, 18.65836968132601], [73.81132887919833, 18.65834896644373], [73.81131128336692, 18.65827612055903], [73.80938929551539, 18.65890554000763], [73.80758003560811, 18.65952179646634], [73.80755559109457, 18.65956480009438], [73.80756995498798, 18.65972815669084], [73.80778848832048, 18.66082521718613], [73.80787705655385, 18.66141673820783]]	primary
94355c30-a64a-45ab-a2fd-988f3c0cc380	F11 Route - MH-14-HG-6749	2026-09-14 16:27:59.898546+00	2026-09-14 16:27:59.898546+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.80704054243614, 18.66479261593898], [73.80701775785182, 18.66430404923349], [73.80683413376104, 18.66337777667988], [73.80681306988828, 18.66333352505423], [73.80633311204707, 18.66342414313108], [73.80633830864275, 18.6635224657013], [73.8064732222517, 18.66434354928106], [73.8065228517659, 18.66436077783143], [73.80692989683958, 18.66427956096656], [73.80694397930918, 18.66432900507138], [73.80652657416907, 18.66439859988688], [73.80570062604282, 18.66452839554377], [73.80560243756192, 18.66455369379485], [73.80537453598872, 18.66362185873597], [73.80537871687996, 18.66358969753832], [73.80493328179736, 18.66367762843841], [73.80489171011496, 18.66369538067103], [73.8050681334783, 18.66446682305961], [73.80516258197336, 18.66501880680304], [73.80511456087947, 18.6650248944236], [73.80502342110192, 18.6645176082595], [73.80469189303138, 18.66457809218644], [73.80428087220167, 18.66466401237746], [73.80412138771847, 18.66407499441233], [73.80394647052074, 18.66329616555976], [73.80373242209184, 18.66239489964706], [73.80363128949769, 18.6619429356182], [73.80361291878931, 18.6618726620786], [73.80398748713453, 18.66177985717207], [73.80424687975497, 18.66288792603884], [73.80460592590158, 18.66451294911875], [73.80461241786969, 18.66455917776592], [73.80500650392494, 18.66446408570349], [73.80483490537571, 18.66370848435863], [73.80461553431189, 18.66287659468936], [73.80449126442913, 18.6622507652552], [73.8043596445684, 18.66165320156716], [73.80424388509581, 18.6610812991577], [73.80423353014086, 18.66104413067811], [73.80501683620325, 18.66082375592979], [73.80501214996966, 18.66077970338729], [73.8046095761101, 18.66088196354589], [73.80455507924944, 18.66088020056485], [73.80448717220905, 18.66056008045787], [73.80447606235565, 18.66052693393786], [73.8034629370095, 18.6607974685377], [73.80337894986455, 18.66082487815378], [73.80334878463852, 18.66085192912898], [73.80334623612673, 18.66091398496346], [73.80341889891618, 18.66116502410082], [73.80344725235456, 18.66117698747512], [73.80414279825266, 18.66099622386526], [73.80415664405336, 18.66104486853148], [73.80346574830415, 18.66121799786656], [73.80345560879518, 18.66123967700564], [73.80359657180524, 18.66180905939287], [73.80360802607063, 18.66182289101044], [73.80362898236474, 18.6618300388138], [73.80396211906077, 18.66174782875058], [73.80388731468571, 18.66141630713157]]	primary
6cbee845-d74f-434e-bcd2-8205b5b13030	F11 Route - MH-14-HG-7113	2026-09-14 16:28:00.026042+00	2026-09-14 16:28:00.026042+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.81245728379731, 18.66354531619894], [73.81260958844248, 18.66596277417469], [73.81261849067735, 18.66602351080956], [73.8127421784028, 18.66605958044721], [73.81279201358726, 18.6666471806643], [73.81274678530617, 18.66673930434526], [73.81271121313955, 18.66678247869735], [73.81267547320543, 18.66685364862737], [73.81267522322166, 18.66691579090166], [73.81283638384444, 18.66852230998193], [73.81286913253645, 18.66851937243375], [73.81275162553742, 18.66714899049144], [73.81272083607665, 18.6668772902882], [73.8127436874275, 18.66680624158264], [73.81279848882538, 18.66675709842206], [73.81283395837902, 18.6666285645701], [73.81281168020936, 18.66647269982804], [73.81280900146085, 18.66610679614441], [73.8129170706097, 18.66610078055323], [73.81294575181442, 18.66612781833542], [73.81303050268427, 18.66680418008475], [73.81331306423708, 18.66862230685138], [73.81333598580377, 18.66859715546461], [73.81323750590636, 18.66791377933596], [73.81308447619006, 18.66696694786662], [73.81298076928617, 18.66613766176206], [73.81303460508778, 18.66607464211086], [73.8131645311621, 18.66605374088552], [73.81322474813713, 18.66605675855769], [73.81326651695264, 18.66611066326944], [73.81333057068159, 18.66639482142042], [73.81359872306797, 18.66779620310956], [73.81371157360435, 18.66839745866872], [73.81375057431978, 18.66839721729093], [73.81354962653242, 18.66718981182706], [73.81348774053353, 18.66687703772649], [73.81329801361214, 18.6660711819797], [73.8132808536887, 18.66600360175338], [73.81337084190379, 18.66597908967456], [73.81314376814146, 18.66459686144034], [73.81317863212418, 18.66456454383134], [73.8132603851717, 18.66500544751674], [73.8134206585643, 18.66596890801188], [73.81349506173588, 18.66597154545709], [73.81360173627402, 18.66595557147074], [73.81368239930329, 18.66594614516886], [73.81346273341892, 18.66455425749641], [73.81349413232513, 18.66454530133108], [73.81372436119753, 18.66591825478251], [73.81399476123212, 18.66584704731514], [73.81387820447162, 18.66504739688332], [73.81391625397804, 18.66503838850683], [73.81405582233877, 18.66585288363489], [73.81456400817818, 18.66571549531427], [73.81460801653935, 18.66572144867156], [73.81476257564971, 18.66646043949156], [73.81379399029979, 18.66663743232522], [73.81380354436953, 18.66667109703489], [73.81473738470353, 18.66650675734311], [73.8147815814, 18.6665216062425], [73.81504571838245, 18.66800716360072], [73.81517883788754, 18.66909786869319], [73.81516988987157, 18.66913616059921], [73.81482738802397, 18.66918482695382], [73.81478990254566, 18.66916175500113], [73.8147387585524, 18.66914136902005], [73.81468527779091, 18.66912585663582], [73.81465058878446, 18.66911551424866], [73.81459352020542, 18.66885537233639], [73.81454907288202, 18.66883522717036], [73.81389160167892, 18.66894782936882], [73.813903772685, 18.6689732910012], [73.81447513696273, 18.66888559221023], [73.81454505983041, 18.66887046726878], [73.81460046751073, 18.66908461803773], [73.81464188576442, 18.66913103123015], [73.81476461117794, 18.66918780927984], [73.8147656138021, 18.6692501060022], [73.81476363774867, 18.66931805839486], [73.81472728066112, 18.66933936893821], [73.81462251822269, 18.66935571586939], [73.81396877482094, 18.66946990096915], [73.81395312054667, 18.6695775238361], [73.81396726777064, 18.66966393427169], [73.81398062013676, 18.66981122087378], [73.81394510483996, 18.66983632534929], [73.81375255050956, 18.66986687636739], [73.81376493331406, 18.66989165687669], [73.81401257995334, 18.66984387170614], [73.814028206318, 18.66981896745283], [73.81399169687224, 18.66954226634052], [73.81400432045689, 18.66952064281367], [73.81470709042672, 18.66937105772279], [73.81477567229717, 18.6693783338588], [73.81479942169226, 18.66941756822962], [73.81486974337555, 18.66981616032796], [73.81489774142945, 18.66981558788697], [73.81483393472733, 18.66936188205383], [73.81482851691572, 18.66924962885146], [73.81483767424591, 18.66920809108201], [73.81514496880075, 18.66918776044546], [73.81519071595088, 18.66920799600581], [73.81521807188561, 18.66945274615042], [73.815331722993, 18.67031194945947], [73.81532409443665, 18.67033944005704], [73.81525712660768, 18.67037254443207], [73.81404855617663, 18.67060326523463], [73.81406336104699, 18.67064402912816], [73.81537441023015, 18.67040793806669], [73.81548445554539, 18.67111390598051], [73.81548787391687, 18.67116530471837], [73.81446538160874, 18.6713278259845], [73.814483953864, 18.67135131292353], [73.81454497183991, 18.67133482121971], [73.81552590851318, 18.6711961192495], [73.81569910213568, 18.67200935975511], [73.81578511456627, 18.67270524695943], [73.81578813756686, 18.67279400130648], [73.8157831568998, 18.67283461146822], [73.81529935197658, 18.6728598666532], [73.81531464364753, 18.67290369082574], [73.81581003892568, 18.67287263910506], [73.81587010090848, 18.67380092594265], [73.81586796713425, 18.67384499680981], [73.81552472863838, 18.67390178973601], [73.81532832287016, 18.67410235385796], [73.81527827117439, 18.67415737875583], [73.81518504905576, 18.67434752964648], [73.81513757399433, 18.67453710245605], [73.81482950323137, 18.67530156563899], [73.81465404250604, 18.67572080706424], [73.81449817765107, 18.67598898047978], [73.81440616148298, 18.67621370238263], [73.81437173661426, 18.67635230090035], [73.81437389008143, 18.67646614052788], [73.81436486014364, 18.67649987788825], [73.8143417870559, 18.67651784941878], [73.81303715729852, 18.67678811622364], [73.81305985150676, 18.67682398661285], [73.81432870427933, 18.67656773491118], [73.81436781499148, 18.6766052463783], [73.81437740933374, 18.67673101486502], [73.81445894606223, 18.67784810496174]]	primary
2c83fece-5042-4133-89cc-f74c37b75b4b	F11 Route - MH-14-KA-2275	2026-09-14 16:28:00.119846+00	2026-09-14 16:28:00.119846+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.79503380463709, 18.66396778119696], [73.79496232922355, 18.66375453990845], [73.79289170334306, 18.66444099407412], [73.79266682692754, 18.66383068710157], [73.79099828492157, 18.66441984402981], [73.79052905358999, 18.66459621520854], [73.79004804476345, 18.66510305624924], [73.78998055260183, 18.66506989589911], [73.78967829738998, 18.66476122749783], [73.78942896167618, 18.66454898224955], [73.78891952652587, 18.66414317389504], [73.78848808856445, 18.66371631921563], [73.78833211398944, 18.66359298345599], [73.78828484933477, 18.66354752694173], [73.78928259085687, 18.66305553321716], [73.79042383105431, 18.66250317016277], [73.790787351399, 18.66225826872543], [73.79142066406469, 18.66405637005543], [73.7914425381078, 18.66417840883194], [73.79169647274882, 18.66410675821637], [73.7926594040698, 18.66378106246978], [73.7917736813253, 18.66171229915149], [73.7908665186692, 18.66219725166901]]	primary
568744da-8f2a-4440-a847-c0b5073bab92	F11 Route - MH-11-M-4303	2026-09-14 16:28:00.195+00	2026-09-14 16:28:00.195+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.80647988308749, 18.66916079050722], [73.80659916674406, 18.66952863048747], [73.80679402244881, 18.66950435834124], [73.80834959896491, 18.66925681234856], [73.80808680671588, 18.66752478100584], [73.80798015728453, 18.66753060539666], [73.80767080468381, 18.66757854617402], [73.80745081205112, 18.66761936805312], [73.80756719891825, 18.66864558581084], [73.80754847543318, 18.66873301184019], [73.80744430153624, 18.66878475820967], [73.80663893662619, 18.66885876070328], [73.806575122883, 18.66886294091981], [73.80642526098049, 18.66882097439652], [73.80635534633123, 18.66874250342297], [73.80626300292344, 18.66806255613873], [73.80632779695034, 18.66797622484363], [73.80634189413779, 18.66796875767779], [73.80635248551714, 18.66796133270594], [73.80643006341643, 18.66786618245532], [73.8065026898944, 18.66774520214282], [73.80650964068944, 18.66766574612954], [73.80661028109597, 18.66762443352409], [73.80735230243394, 18.6674838265847], [73.80798830902117, 18.66733695816012], [73.80804825705505, 18.66728010357246], [73.80787644636379, 18.66613533695665], [73.80773605255092, 18.66546308830275], [73.80772275423821, 18.6653411866654], [73.80771056843243, 18.66524914481702], [73.80759648282068, 18.6652126281006], [73.80613927415963, 18.66552106787249], [73.80603077959668, 18.66555887654945], [73.80593543294138, 18.66558104855043], [73.80592375972007, 18.66571619197428], [73.8060072430817, 18.66644669170605], [73.80616638542155, 18.66643553046481], [73.80715221854489, 18.66630292309326], [73.80722710137728, 18.66634443845182], [73.80726886195816, 18.66663508172941], [73.80738181815249, 18.66735656986403], [73.80738718050848, 18.66735352641443], [73.80738011243962, 18.66742057300555], [73.80731469625417, 18.66747048730219], [73.80650541971409, 18.66761066111348], [73.80644926189382, 18.66756999400431], [73.8063997093496, 18.66749820428547], [73.80631257493715, 18.6674013179615], [73.80614839959378, 18.6673583728132], [73.80609556660274, 18.66730862366308], [73.80595858606671, 18.66662548296805], [73.80597638255628, 18.66651356118914], [73.80598364529727, 18.66646537799416]]	primary
59a95884-3a00-4f95-bfc8-6a993461bd88	F11 Route - MH-14-KA-2273	2026-09-14 16:28:00.314126+00	2026-09-14 16:28:00.314126+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.80453567855257, 18.66982317309495], [73.80475666475405, 18.67043518456901], [73.80491736851015, 18.67121679223607], [73.80496182006435, 18.67132425221081], [73.80513447774712, 18.67132970116665], [73.80518323483788, 18.6713042186395], [73.80499020570566, 18.67040699482375], [73.80519780558477, 18.67039668551657], [73.80537792867905, 18.67124219014094], [73.80629162048332, 18.67122826929477], [73.8063526535375, 18.67115145917219], [73.80620001210512, 18.66985353171529], [73.80616100349575, 18.66957779138954], [73.81173204358876, 18.66376903667286], [73.8115421948757, 18.66384229929517], [73.81153732491808, 18.66395823909473], [73.81159734806769, 18.6643863324978], [73.81156802587502, 18.66440458940991], [73.81148842594008, 18.66388021704907], [73.81147809986821, 18.66385196805953], [73.8109991917213, 18.66400751098508], [73.81096698241853, 18.66402586061404], [73.8110997788054, 18.66463712722827], [73.81109645279025, 18.66466378848195], [73.81106754703197, 18.66467734522005], [73.81093065548073, 18.66405445413706], [73.81088738616019, 18.6640489532754], [73.80947098245946, 18.66454309358536], [73.80787883838416, 18.66512924634625], [73.80785245407226, 18.66513984938941], [73.80779336226715, 18.66520045402143], [73.80811703921722, 18.66621711829519], [73.80870093097329, 18.66878683660724], [73.80880682144482, 18.66928616968159], [73.808978731343, 18.66991572533836], [73.80908741066607, 18.6703923819585], [73.80934674928916, 18.6717461405886], [73.80942300499864, 18.671747043734], [73.80902677718234, 18.66985792304117], [73.80871706678953, 18.6686579553287], [73.808224914305, 18.6664335104067], [73.80817511768856, 18.66621500649967], [73.80817248348875, 18.66617293152071], [73.80917459106777, 18.66591052885137], [73.80919512234948, 18.66595671249237], [73.80922005745511, 18.66598195992053], [73.80945596274024, 18.66734023529752], [73.80948841273153, 18.66733232991021], [73.80924474074217, 18.66592192693656], [73.80926720350975, 18.66589131373846], [73.80933674018162, 18.66587043984234], [73.80939590893047, 18.66585911779588], [73.81028110864614, 18.66563801266001], [73.81035182107381, 18.66561213538938], [73.81041900403184, 18.66624884382063], [73.8104489870256, 18.66625172742861], [73.81047637973008, 18.6662450026181], [73.81037654930782, 18.6655983367503], [73.81038199475412, 18.66556312912583], [73.8106388946318, 18.66551404240406], [73.81068768218432, 18.66552794457831], [73.81087426113966, 18.66700419393079], [73.81098804106551, 18.66809363922771], [73.81114388400073, 18.66935106996171], [73.81117500446294, 18.66937079162377], [73.81107157327165, 18.66851082486642], [73.81091558033351, 18.66707237708554], [73.81081612687191, 18.66624484142739], [73.81072656857721, 18.66551666242931], [73.81076205346028, 18.6655002124007], [73.81084761095454, 18.66550263223178], [73.8109753951784, 18.66589168513321], [73.81101791545434, 18.66589011976231], [73.81089051049709, 18.66550176970541], [73.8109117272162, 18.66546969886954], [73.81092510634592, 18.66546577368799], [73.81124663623797, 18.66553073691419], [73.8112713279599, 18.66550396296659], [73.81125324547861, 18.66544913366719], [73.81085153093544, 18.66542884064627], [73.81025741308002, 18.66556607749882], [73.8099388852769, 18.66566716967258], [73.80924118205124, 18.6658469957438], [73.8092226716591, 18.6657811544129], [73.80914736263102, 18.66506846523464], [73.80912808824455, 18.66505917555756], [73.80908516516602, 18.66506650484557], [73.80918556798682, 18.66583333305472], [73.80919703123014, 18.6658654041962], [73.80616434340799, 18.66957452670665], [73.8062379308948, 18.6695603358794], [73.80633066048921, 18.66955813459155], [73.80620829974524, 18.66898307350772], [73.80622911876996, 18.66889117595984], [73.80630178630611, 18.66880417845238], [73.8062210834902, 18.66801057751586], [73.80635414630791, 18.66794314959891], [73.80643202791175, 18.66785754933091], [73.80647950336953, 18.66770164395035], [73.80644717785692, 18.66757893931334], [73.80628273277065, 18.6674005882348], [73.80620556286733, 18.66737554311695], [73.80615014933709, 18.66736862538816], [73.80606863073032, 18.66736888051555], [73.80594434212811, 18.666527577729], [73.80597686899283, 18.66644844982599], [73.80600145951455, 18.66637716098629], [73.80595768287782, 18.66560941682387], [73.8060770451988, 18.66559975301132], [73.80653128638076, 18.66554445336095], [73.80707867981455, 18.66538457212302], [73.80764851848966, 18.66519631056671], [73.80792002896813, 18.66502015918122], [73.80867891018781, 18.66472534675965], [73.81053350998218, 18.66405622642749], [73.81084983379367, 18.66394370164672], [73.81128928442953, 18.66379427646779], [73.8115063492033, 18.66372302688634], [73.81162387644892, 18.66369248740985], [73.81175371470765, 18.6636616085912], [73.81177872632976, 18.66371218033933], [73.81178149797995, 18.66376866202867], [73.81172893782261, 18.66377007314883]]	primary
89d1bdd1-3a69-426f-902f-8b7a8f819086	F11 Route - MH-14-HG-7121	2026-09-14 16:28:00.398484+00	2026-09-14 16:28:00.398484+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.80450683252043, 18.67462413871786], [73.80559836316039, 18.67539171050017], [73.80621038665718, 18.67565293110209], [73.80656908015425, 18.675825848843], [73.8068402591065, 18.67593241099092], [73.80710515408667, 18.67600439057145], [73.80725329905756, 18.67608433776875], [73.80733108226515, 18.67615371919464], [73.80737576585857, 18.67625037765284], [73.80751708690235, 18.67656476704967], [73.80759247227333, 18.67681971565665], [73.80766972911621, 18.67710943668583], [73.80771165897873, 18.67724746740601], [73.8078281273074, 18.6773223955159], [73.808031596348, 18.67738546236517], [73.8085298363003, 18.67745056019332], [73.80861893306705, 18.67746630201723], [73.8087918329867, 18.67754334575675], [73.8088520966806, 18.67769463132482], [73.8091319111823, 18.67845071357453], [73.80921051575012, 18.67855640744678], [73.80974473298518, 18.67887668231708], [73.80980859237246, 18.6788788894806], [73.80983597387727, 18.67880710478078], [73.80932938561637, 18.67856653384152], [73.80922025181775, 18.67843141549323], [73.80894637255888, 18.67775119446675], [73.80891070643594, 18.6775888331744], [73.80881121643917, 18.67744730850869], [73.80872999802305, 18.67741881042495], [73.80855868699096, 18.67738749067206], [73.80841678579168, 18.67736647264445], [73.80806379932719, 18.67735322009771], [73.80779157052916, 18.6772435635845], [73.80759531406518, 18.6765825651582], [73.80754456407749, 18.67644098159396], [73.80747983853183, 18.6762658020749], [73.80742364143201, 18.67615273099918], [73.80737615767896, 18.67607568045051], [73.80732048080105, 18.67602144049475], [73.8070555375633, 18.67477034119359], [73.80703881318463, 18.67467623690596], [73.80714887562486, 18.67459137786915], [73.80733087021336, 18.67457767486658], [73.8095187624747, 18.674188609931], [73.8096295689689, 18.67415463037129], [73.8096950509502, 18.67401282516141], [73.80974463645124, 18.67395922515747], [73.80984787831972, 18.67394449949564], [73.81004958227679, 18.67394302605083], [73.81014656783128, 18.67402867167069], [73.81070710060696, 18.67574177546085], [73.81100222147792, 18.6767907045539], [73.81115668176112, 18.67713964043083], [73.81130913335261, 18.67766672987574], [73.8113128084532, 18.67789101196291], [73.81128665710523, 18.67836422226622], [73.81134013460448, 18.67840214088399], [73.81137272908775, 18.6782926067257], [73.81138034347815, 18.67798477362078], [73.81138433963484, 18.67773921192446], [73.8113510340386, 18.67756533724396], [73.81127234809466, 18.6773349359727], [73.81114158740961, 18.67701124336087], [73.81102081314411, 18.67662104168383], [73.81091563898666, 18.67636122890772], [73.81075093248657, 18.67577655552998], [73.81065345021548, 18.67543531941076], [73.8106175328424, 18.67533337893373], [73.81054026934962, 18.67508865870571], [73.81047875696818, 18.67484790238351], [73.81042885116828, 18.67465175997228], [73.81037853432638, 18.67445873693897], [73.81029045968488, 18.67422148542009], [73.81024814684194, 18.67406152753134], [73.81022336941918, 18.67396854735878], [73.81017840482158, 18.67391346507936], [73.81008762774333, 18.67388065323674], [73.8099544519915, 18.67385938066005], [73.80984315421138, 18.67386381330504], [73.8097722584119, 18.67373800447947], [73.80975209055474, 18.67362124039168], [73.80972988634191, 18.67342808817458], [73.80961834988024, 18.67287738908801], [73.80958890334365, 18.67267844574694], [73.80955488827863, 18.67255623177757], [73.80949697477702, 18.67229479396802], [73.80947242160488, 18.67197064518664], [73.80939812954561, 18.67183987717737], [73.80910475571243, 18.67181783403079], [73.80859138676148, 18.67190976770414], [73.80835705094427, 18.67195975910295], [73.80817385261194, 18.67196016421365], [73.80686644823568, 18.67216388194413], [73.80664633982232, 18.67222967600304], [73.80654264692193, 18.67227311971469], [73.80655694522552, 18.67237376395668], [73.80674279837393, 18.67339282842338], [73.80678602569306, 18.67342654465981], [73.80788301145995, 18.67327072733175], [73.80790949328154, 18.67332513356319], [73.80781875230198, 18.67334836281454], [73.80676948976178, 18.67348339395766], [73.8066952860344, 18.67349208846594], [73.80646554793127, 18.67223725828568], [73.80629185829387, 18.67130284201365], [73.80617365410671, 18.67123704876889], [73.80604533102, 18.6712420032177], [73.80522861225225, 18.67128311966916], [73.80518823734224, 18.67134386574872], [73.80523323378239, 18.6715735750273], [73.80534614353262, 18.67211781111384], [73.80530468757827, 18.67226544206914], [73.8052830009787, 18.67237372579963], [73.80527078919809, 18.67248463843683], [73.80536552102083, 18.67296883783865], [73.80536224749244, 18.6730462457936], [73.8053231826554, 18.67307844099897], [73.8050941579094, 18.67313054947067], [73.8050743712932, 18.67324315525259], [73.80507187917507, 18.67325998125676], [73.80524550384817, 18.67495457209489]]	primary
c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	F11 Route - MH-14-JL-1325	2026-09-14 16:28:00.475412+00	2026-09-14 16:28:00.475412+00	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	dcaaab0b-77f3-4766-9782-76814d1d4faa	[[73.80386656673338, 18.66587983385133], [73.80400912634995, 18.6669037892446], [73.80408406182116, 18.66723307971454], [73.80420092144813, 18.66772270774715], [73.80420127045716, 18.66782190963618], [73.80425473264678, 18.66787054477109], [73.80467600185045, 18.66778905027152], [73.80479231091257, 18.66776699658808], [73.80485341340884, 18.66769695905046], [73.80473931834914, 18.6668826060858], [73.80469457691137, 18.66671699471063], [73.80480219739898, 18.66667779810096], [73.80494273874791, 18.66663904030551], [73.80556772403267, 18.66654685546351], [73.80582682348711, 18.66648688381362], [73.80591446473859, 18.66652321718184], [73.80597178952503, 18.66667929200176], [73.80607892583978, 18.66735172193965], [73.80593798083741, 18.66740841092541], [73.80586309290271, 18.66749479014181], [73.80579104906784, 18.66761917468277], [73.8057602641288, 18.66771125245646], [73.805768134405, 18.66775010160869], [73.80489790633834, 18.66786932599022], [73.80484495007558, 18.66794388670621], [73.80483352371172, 18.66799117028935], [73.80428851059219, 18.66805114260859], [73.80423320360528, 18.66819233945411], [73.80440584078781, 18.6694406208436], [73.80451077763482, 18.66983321798058], [73.80476188263849, 18.66982268670009], [73.80627225138355, 18.66957779052443], [73.80619325639215, 18.66897338410674], [73.80615725979257, 18.66891723464649], [73.80602428257598, 18.66890781384361], [73.80511044795595, 18.66906220583248], [73.80503412545401, 18.66899736144508], [73.80499661438942, 18.66888756685261], [73.80488538404731, 18.66800650063437], [73.80489340636932, 18.66794086670301], [73.80494904307939, 18.66791257978466], [73.8049559450597, 18.66791261005964], [73.80527545187523, 18.66784833906387], [73.80579857573903, 18.66778501021612], [73.80586609512908, 18.66790433177208], [73.80597947149695, 18.66796682398299], [73.8061186349331, 18.66802366127641], [73.80612607424533, 18.66802741267024], [73.80621744262424, 18.66805457640458], [73.8062178397179, 18.66823337642027], [73.80628540561203, 18.66866094062165], [73.80629547541865, 18.66879085857188], [73.80636445463567, 18.66887047872399], [73.80645550015956, 18.66890510671522], [73.8065341613557, 18.66945015533894], [73.80659916674406, 18.66952863048747]]	primary
\.


--
-- Data for Name: secondary_vehicle_assignments; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.secondary_vehicle_assignments (id, vehicle_id, gtc_pickup_point_id, dump_yard_id, material_type, assigned_from, assigned_to, active, remarks, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: system_configurations; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.system_configurations (id, config_key, config_type, description, value, active, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ticket_comments; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.ticket_comments (id, ticket_id, author, content, is_internal, created_at) FROM stdin;
\.


--
-- Data for Name: tickets; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.tickets (id, title, description, category, priority, status, due_at, assigned_to, created_by, related_alert_id, related_truck_id, related_driver_id, escalation_level, sla_breached, metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: vehicles; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.vehicles (id, vehicle_number, registration_number, truck_type, capacity_kg, capacity_cubic_meter, ward_id, route_id, fuel_type, operational_status, chassis_number, engine_number, manufacture_year, active, metadata, created_at, updated_at, vendor_id, vehicle_category, secondary_waste_type) FROM stdin;
1efc3e3f-cd86-4d33-9119-01037b52a7e7	MH04EY5266-BVG	MH04EY5266-BVG	Truck	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.589042+00	2026-09-14 12:29:13.589042+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
1668dc55-77d2-432a-9880-0dc1e6e12093	MH14HG6943-BVG	MH14HG6943-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.605243+00	2026-09-14 12:29:13.605243+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
4ea37df4-44a9-4cc1-9c87-190ca0212748	MH12AR5729-BVG	MH12AR5729-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.620955+00	2026-09-14 12:29:13.620955+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
44ac0a5a-196b-4977-a678-f72e124636af	MH14LB8529-BVG	MH14LB8529-BVG	CamperVan	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.67831+00	2026-09-14 12:29:13.67831+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
802526ee-08fe-440f-9cec-2d940134471b	MH14LX9984-BVG	MH14LX9984-BVG	CamperVan	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.708119+00	2026-09-14 12:29:13.708119+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
7c130b1b-f989-4c93-8c87-7a5ccddaae8c	MH14KA2271-BVG	MH14KA2271-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.722599+00	2026-09-14 12:29:13.722599+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
0abf29e2-4772-4dc9-a0db-5b1ed139d89b	MH14LB0053-BVG	MH14LB0053-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	\N	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.750183+00	2026-09-14 12:29:13.750183+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
10cc4968-5ab9-49b3-9593-91fb1d96db7f	MH14HG6954-BVG	MH14HG6954-BVG	CamperVan	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	17c994ed-d970-46e1-a4af-26152eaa8b8b	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.649595+00	2026-09-14 15:53:32.827613+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
54b02dc0-f719-45c9-8a0d-b6e6e748acfd	MH14HG6950-BVG	MH14HG6950-BVG	Truck	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	5b2a6017-c8ba-47a5-a41c-62d9843ad666	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.573127+00	2026-09-14 16:27:59.781158+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
ef8fbf24-5944-49a1-a97b-fa47c522511f	MH14HG6749-BVG	MH14HG6749-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	94355c30-a64a-45ab-a2fd-988f3c0cc380	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.664127+00	2026-09-14 16:27:59.929932+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
26282ab7-d30e-4480-a6e0-f4363376b47f	MH14HG7113-BVG	MH14HG7113-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	6cbee845-d74f-434e-bcd2-8205b5b13030	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.764277+00	2026-09-14 16:28:00.043604+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
8fadfe4c-e423-42ae-ba7a-63f889b1802a	MH14KA2275-BVG	MH14KA2275-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	2c83fece-5042-4133-89cc-f74c37b75b4b	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.777982+00	2026-09-14 16:28:00.133528+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
97b370c6-1cce-4cbd-82f0-d9a739d475df	MH11M4303-BVG	MH11M4303-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	568744da-8f2a-4440-a847-c0b5073bab92	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.736181+00	2026-09-14 16:28:00.210222+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
12f47f2f-71e9-4b92-9144-8c3528b23b35	MH14KA2273-BVG	MH14KA2273-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	59a95884-3a00-4f95-bfc8-6a993461bd88	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.63525+00	2026-09-14 16:28:00.331593+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
72742592-59b8-4409-b9b6-eedd702ba23b	MH14HG7121-BVG	MH14HG7121-BVG	Truck	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	89d1bdd1-3a69-426f-902f-8b7a8f819086	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.556291+00	2026-09-14 16:28:00.415249+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
74a3dd39-b709-4c75-8fb3-e7eef3b4b52b	MH14JL1325-BVG	MH14JL1325-BVG	Car	0	0	dcaaab0b-77f3-4766-9782-76814d1d4faa	c9f6d7d6-e55f-47ac-949c-244d9f85ebbe	diesel	operational	\N	\N	\N	t	{}	2026-09-14 12:29:13.693392+00	2026-09-14 16:28:00.483497+00	035536c7-c0b2-4427-8908-12e7a1fb36eb	primary	\N
\.


--
-- Data for Name: vendors; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.vendors (id, vendor_code, vendor_name, contact_person, email, phone, webhook_secret, signature_key, allowed_ips, auth_type, callback_format, active, metadata, created_at, updated_at) FROM stdin;
035536c7-c0b2-4427-8908-12e7a1fb36eb	ZONEF	Zone-F	\N	\N	0000000000	\N	\N	[]	header	{}	t	{}	2026-09-14 12:29:13.532454+00	2026-09-14 12:29:13.532454+00
\.


--
-- Data for Name: wards; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.wards (id, ward_name, active, created_at, updated_at, ward_code, zone_id, population, area, total_pickup_points) FROM stdin;
dcaaab0b-77f3-4766-9782-76814d1d4faa	F11	t	2026-09-14 12:29:13.515643+00	2026-09-14 12:29:13.515643+00	F11	d45eb94a-ac06-42f1-b3a0-932d6df92e0e	\N	\N	\N
\.


--
-- Data for Name: zones; Type: TABLE DATA; Schema: public; Owner: swm
--

COPY public.zones (id, zone_code, zone_name, active, created_at, updated_at, description, supervisor_name, supervisor_phone) FROM stdin;
d45eb94a-ac06-42f1-b3a0-932d6df92e0e	ZONEF	Zone-F	t	2026-09-14 12:29:13.503875+00	2026-09-14 12:29:13.503875+00	\N	\N	\N
\.


--
-- Data for Name: geocode_settings; Type: TABLE DATA; Schema: tiger; Owner: swm
--

COPY tiger.geocode_settings (name, setting, unit, category, short_desc) FROM stdin;
\.


--
-- Data for Name: pagc_gaz; Type: TABLE DATA; Schema: tiger; Owner: swm
--

COPY tiger.pagc_gaz (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_lex; Type: TABLE DATA; Schema: tiger; Owner: swm
--

COPY tiger.pagc_lex (id, seq, word, stdword, token, is_custom) FROM stdin;
\.


--
-- Data for Name: pagc_rules; Type: TABLE DATA; Schema: tiger; Owner: swm
--

COPY tiger.pagc_rules (id, rule, is_custom) FROM stdin;
\.


--
-- Data for Name: topology; Type: TABLE DATA; Schema: topology; Owner: swm
--

COPY topology.topology (id, name, srid, "precision", hasz) FROM stdin;
\.


--
-- Data for Name: layer; Type: TABLE DATA; Schema: topology; Owner: swm
--

COPY topology.layer (topology_id, layer_id, schema_name, table_name, feature_column, feature_type, level, child_id) FROM stdin;
\.


--
-- Name: device_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: swm
--

SELECT pg_catalog.setval('public.device_events_id_seq', 402626, true);


--
-- Name: gtc_checkpoints_id_seq; Type: SEQUENCE SET; Schema: public; Owner: swm
--

SELECT pg_catalog.setval('public.gtc_checkpoints_id_seq', 1, false);


--
-- Name: topology_id_seq; Type: SEQUENCE SET; Schema: topology; Owner: swm
--

SELECT pg_catalog.setval('topology.topology_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: device_events device_events_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.device_events
    ADD CONSTRAINT device_events_pkey PRIMARY KEY (id);


--
-- Name: dump_yard_weighments dump_yard_weighments_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yard_weighments
    ADD CONSTRAINT dump_yard_weighments_pkey PRIMARY KEY (id);


--
-- Name: dump_yards dump_yards_dump_yard_code_key; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yards
    ADD CONSTRAINT dump_yards_dump_yard_code_key UNIQUE (dump_yard_code);


--
-- Name: dump_yards dump_yards_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yards
    ADD CONSTRAINT dump_yards_pkey PRIMARY KEY (id);


--
-- Name: gts_points gts_points_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.gts_points
    ADD CONSTRAINT gts_points_pkey PRIMARY KEY (id);


--
-- Name: pickup_point_crossings pickup_point_crossings_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_point_crossings
    ADD CONSTRAINT pickup_point_crossings_pkey PRIMARY KEY (id);


--
-- Name: alert_actions pk_alert_actions; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.alert_actions
    ADD CONSTRAINT pk_alert_actions PRIMARY KEY (id);


--
-- Name: alerts pk_alerts; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT pk_alerts PRIMARY KEY (id);


--
-- Name: analytics_daily_kpis pk_analytics_daily_kpis; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.analytics_daily_kpis
    ADD CONSTRAINT pk_analytics_daily_kpis PRIMARY KEY (metric_date, vehicle_id);


--
-- Name: analytics_geofence_events pk_analytics_geofence_events; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.analytics_geofence_events
    ADD CONSTRAINT pk_analytics_geofence_events PRIMARY KEY (id);


--
-- Name: analytics_idle_records pk_analytics_idle_records; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.analytics_idle_records
    ADD CONSTRAINT pk_analytics_idle_records PRIMARY KEY (id);


--
-- Name: analytics_overspeed_events pk_analytics_overspeed_events; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.analytics_overspeed_events
    ADD CONSTRAINT pk_analytics_overspeed_events PRIMARY KEY (id);


--
-- Name: analytics_trip_records pk_analytics_trip_records; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.analytics_trip_records
    ADD CONSTRAINT pk_analytics_trip_records PRIMARY KEY (id);


--
-- Name: analytics_vehicle_state pk_analytics_vehicle_state; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.analytics_vehicle_state
    ADD CONSTRAINT pk_analytics_vehicle_state PRIMARY KEY (vehicle_id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: auth_permissions pk_auth_permissions; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_permissions
    ADD CONSTRAINT pk_auth_permissions PRIMARY KEY (id);


--
-- Name: auth_refresh_tokens pk_auth_refresh_tokens; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT pk_auth_refresh_tokens PRIMARY KEY (id);


--
-- Name: auth_role_permissions pk_auth_role_permissions; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_role_permissions
    ADD CONSTRAINT pk_auth_role_permissions PRIMARY KEY (role_id, permission_id);


--
-- Name: auth_roles pk_auth_roles; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_roles
    ADD CONSTRAINT pk_auth_roles PRIMARY KEY (id);


--
-- Name: auth_user_roles pk_auth_user_roles; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_user_roles
    ADD CONSTRAINT pk_auth_user_roles PRIMARY KEY (user_id, role_id);


--
-- Name: auth_users pk_auth_users; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_users
    ADD CONSTRAINT pk_auth_users PRIMARY KEY (id);


--
-- Name: devices pk_devices; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT pk_devices PRIMARY KEY (id);


--
-- Name: drivers pk_drivers; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.drivers
    ADD CONSTRAINT pk_drivers PRIMARY KEY (id);


--
-- Name: device_vehicle_assignments pk_dva; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.device_vehicle_assignments
    ADD CONSTRAINT pk_dva PRIMARY KEY (device_id, vehicle_id, assigned_from);


--
-- Name: geofences pk_geofences; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.geofences
    ADD CONSTRAINT pk_geofences PRIMARY KEY (id);


--
-- Name: gtc_checkpoints pk_gtc_checkpoints; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.gtc_checkpoints
    ADD CONSTRAINT pk_gtc_checkpoints PRIMARY KEY (id);


--
-- Name: operational_categories pk_operational_categories; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.operational_categories
    ADD CONSTRAINT pk_operational_categories PRIMARY KEY (id);


--
-- Name: pickup_points pk_pickup_points; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_points
    ADD CONSTRAINT pk_pickup_points PRIMARY KEY (id);


--
-- Name: routes pk_routes; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT pk_routes PRIMARY KEY (id);


--
-- Name: system_configurations pk_system_configurations; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.system_configurations
    ADD CONSTRAINT pk_system_configurations PRIMARY KEY (id);


--
-- Name: ticket_comments pk_ticket_comments; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.ticket_comments
    ADD CONSTRAINT pk_ticket_comments PRIMARY KEY (id);


--
-- Name: tickets pk_tickets; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT pk_tickets PRIMARY KEY (id);


--
-- Name: vehicles pk_vehicles; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT pk_vehicles PRIMARY KEY (id);


--
-- Name: vendors pk_vendors; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vendors
    ADD CONSTRAINT pk_vendors PRIMARY KEY (id);


--
-- Name: wards pk_wards; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT pk_wards PRIMARY KEY (id);


--
-- Name: secondary_vehicle_assignments secondary_vehicle_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.secondary_vehicle_assignments
    ADD CONSTRAINT secondary_vehicle_assignments_pkey PRIMARY KEY (id);


--
-- Name: auth_permissions uq_auth_permissions_permission_key; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_permissions
    ADD CONSTRAINT uq_auth_permissions_permission_key UNIQUE (permission_key);


--
-- Name: auth_refresh_tokens uq_auth_refresh_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT uq_auth_refresh_tokens_token_hash UNIQUE (token_hash);


--
-- Name: auth_roles uq_auth_roles_role_key; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_roles
    ADD CONSTRAINT uq_auth_roles_role_key UNIQUE (role_key);


--
-- Name: auth_users uq_auth_users_email; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_users
    ADD CONSTRAINT uq_auth_users_email UNIQUE (email);


--
-- Name: auth_users uq_auth_users_username; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_users
    ADD CONSTRAINT uq_auth_users_username UNIQUE (username);


--
-- Name: geofences uq_geofences_geofence_code; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.geofences
    ADD CONSTRAINT uq_geofences_geofence_code UNIQUE (geofence_code);


--
-- Name: operational_categories uq_operational_categories_category_code; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.operational_categories
    ADD CONSTRAINT uq_operational_categories_category_code UNIQUE (category_code);


--
-- Name: system_configurations uq_system_configurations_config_key; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.system_configurations
    ADD CONSTRAINT uq_system_configurations_config_key UNIQUE (config_key);


--
-- Name: vehicles uq_vehicles_registration_number; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT uq_vehicles_registration_number UNIQUE (registration_number);


--
-- Name: vehicles uq_vehicles_vehicle_number; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT uq_vehicles_vehicle_number UNIQUE (vehicle_number);


--
-- Name: vendors uq_vendors_vendor_code; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vendors
    ADD CONSTRAINT uq_vendors_vendor_code UNIQUE (vendor_code);


--
-- Name: wards uq_wards_ward_code; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT uq_wards_ward_code UNIQUE (ward_code);


--
-- Name: zones zones_pkey; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.zones
    ADD CONSTRAINT zones_pkey PRIMARY KEY (id);


--
-- Name: zones zones_zone_code_key; Type: CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.zones
    ADD CONSTRAINT zones_zone_code_key UNIQUE (zone_code);


--
-- Name: ix_alert_actions_alert_created; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_alert_actions_alert_created ON public.alert_actions USING btree (alert_id, created_at);


--
-- Name: ix_alerts_category; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_alerts_category ON public.alerts USING btree (category);


--
-- Name: ix_alerts_status; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_alerts_status ON public.alerts USING btree (status);


--
-- Name: ix_alerts_vehicle_ts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_alerts_vehicle_ts ON public.alerts USING btree (vehicle_id, triggered_at);


--
-- Name: ix_analytics_daily_kpis_metric_date; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_daily_kpis_metric_date ON public.analytics_daily_kpis USING btree (metric_date);


--
-- Name: ix_analytics_daily_kpis_vendor_date; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_daily_kpis_vendor_date ON public.analytics_daily_kpis USING btree (vendor_id, metric_date);


--
-- Name: ix_analytics_geofence_code_ts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_geofence_code_ts ON public.analytics_geofence_events USING btree (geofence_code, event_ts);


--
-- Name: ix_analytics_geofence_vehicle_ts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_geofence_vehicle_ts ON public.analytics_geofence_events USING btree (vehicle_id, event_ts);


--
-- Name: ix_analytics_idle_records_started; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_idle_records_started ON public.analytics_idle_records USING btree (started_at);


--
-- Name: ix_analytics_idle_records_vehicle_started; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_idle_records_vehicle_started ON public.analytics_idle_records USING btree (vehicle_id, started_at);


--
-- Name: ix_analytics_overspeed_event_ts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_overspeed_event_ts ON public.analytics_overspeed_events USING btree (event_ts);


--
-- Name: ix_analytics_overspeed_vehicle_ts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_overspeed_vehicle_ts ON public.analytics_overspeed_events USING btree (vehicle_id, event_ts);


--
-- Name: ix_analytics_trip_records_started; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_trip_records_started ON public.analytics_trip_records USING btree (started_at);


--
-- Name: ix_analytics_trip_records_vehicle_started; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_trip_records_vehicle_started ON public.analytics_trip_records USING btree (vehicle_id, started_at);


--
-- Name: ix_analytics_vehicle_state_imei; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_analytics_vehicle_state_imei ON public.analytics_vehicle_state USING btree (imei);


--
-- Name: ix_audit_logs_actor; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_audit_logs_actor ON public.audit_logs USING btree (actor);


--
-- Name: ix_audit_logs_created; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_audit_logs_created ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_logs_entity; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_audit_logs_entity ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: ix_auth_permissions_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_permissions_active ON public.auth_permissions USING btree (active);


--
-- Name: ix_auth_permissions_deleted_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_permissions_deleted_at ON public.auth_permissions USING btree (deleted_at);


--
-- Name: ix_auth_permissions_permission_name; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_permissions_permission_name ON public.auth_permissions USING btree (permission_name);


--
-- Name: ix_auth_refresh_tokens_expires_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_refresh_tokens_expires_at ON public.auth_refresh_tokens USING btree (expires_at);


--
-- Name: ix_auth_refresh_tokens_revoked_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_refresh_tokens_revoked_at ON public.auth_refresh_tokens USING btree (revoked_at);


--
-- Name: ix_auth_refresh_tokens_token_family_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_refresh_tokens_token_family_id ON public.auth_refresh_tokens USING btree (token_family_id);


--
-- Name: ix_auth_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_refresh_tokens_user_id ON public.auth_refresh_tokens USING btree (user_id);


--
-- Name: ix_auth_roles_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_roles_active ON public.auth_roles USING btree (active);


--
-- Name: ix_auth_roles_deleted_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_roles_deleted_at ON public.auth_roles USING btree (deleted_at);


--
-- Name: ix_auth_roles_role_name; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_roles_role_name ON public.auth_roles USING btree (role_name);


--
-- Name: ix_auth_users_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_users_active ON public.auth_users USING btree (active);


--
-- Name: ix_auth_users_deleted_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_users_deleted_at ON public.auth_users USING btree (deleted_at);


--
-- Name: ix_auth_users_email; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_users_email ON public.auth_users USING btree (email);


--
-- Name: ix_auth_users_username; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_auth_users_username ON public.auth_users USING btree (username);


--
-- Name: ix_device_events_device_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_device_events_device_id ON public.device_events USING btree (device_id);


--
-- Name: ix_device_events_ts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_device_events_ts ON public.device_events USING btree (ts);


--
-- Name: ix_devices_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_devices_active ON public.devices USING btree (active);


--
-- Name: ix_devices_imei; Type: INDEX; Schema: public; Owner: swm
--

CREATE UNIQUE INDEX ix_devices_imei ON public.devices USING btree (imei);


--
-- Name: ix_devices_last_seen; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_devices_last_seen ON public.devices USING btree (last_seen);


--
-- Name: ix_devices_vendor_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_devices_vendor_id ON public.devices USING btree (vendor_id);


--
-- Name: ix_drivers_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_drivers_active ON public.drivers USING btree (active);


--
-- Name: ix_drivers_name; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_drivers_name ON public.drivers USING btree (name);


--
-- Name: ix_drivers_person_type; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_drivers_person_type ON public.drivers USING btree (person_type);


--
-- Name: ix_drivers_vendor_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_drivers_vendor_id ON public.drivers USING btree (vendor_id);


--
-- Name: ix_dump_yard_weighments_material; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dump_yard_weighments_material ON public.dump_yard_weighments USING btree (material_type);


--
-- Name: ix_dump_yard_weighments_service_date; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dump_yard_weighments_service_date ON public.dump_yard_weighments USING btree (service_date);


--
-- Name: ix_dump_yard_weighments_vehicle_date; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dump_yard_weighments_vehicle_date ON public.dump_yard_weighments USING btree (vehicle_id, service_date);


--
-- Name: ix_dump_yards_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dump_yards_active ON public.dump_yards USING btree (active);


--
-- Name: ix_dump_yards_zone_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dump_yards_zone_id ON public.dump_yards USING btree (zone_id);


--
-- Name: ix_dva_device_assigned_from; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dva_device_assigned_from ON public.device_vehicle_assignments USING btree (device_id, assigned_from);


--
-- Name: ix_dva_vehicle_assigned_from; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_dva_vehicle_assigned_from ON public.device_vehicle_assignments USING btree (vehicle_id, assigned_from);


--
-- Name: ix_geofences_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_active ON public.geofences USING btree (active);


--
-- Name: ix_geofences_circle_gist; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_circle_gist ON public.geofences USING gist (public.geography(public.st_setsrid(public.st_makepoint(center_lng, center_lat), 4326))) WHERE (((geometry_type)::text = 'circle'::text) AND (center_lat IS NOT NULL) AND (center_lng IS NOT NULL));


--
-- Name: ix_geofences_for_hierarchy; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_for_hierarchy ON public.geofences USING btree (geofence_for, zone_id, ward_id, route_id);


--
-- Name: ix_geofences_polygon_gist; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_polygon_gist ON public.geofences USING gist (public.st_setsrid(public.st_geomfromgeojson((polygon)::text), 4326)) WHERE (((geometry_type)::text = 'polygon'::text) AND (polygon IS NOT NULL));


--
-- Name: ix_geofences_route_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_route_id ON public.geofences USING btree (route_id);


--
-- Name: ix_geofences_scope; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_scope ON public.geofences USING btree (scope_type, scope_id);


--
-- Name: ix_geofences_ward_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_ward_id ON public.geofences USING btree (ward_id);


--
-- Name: ix_geofences_zone_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_geofences_zone_id ON public.geofences USING btree (zone_id);


--
-- Name: ix_gtc_checkpoints_arrived_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_gtc_checkpoints_arrived_at ON public.gtc_checkpoints USING btree (arrived_at);


--
-- Name: ix_gtc_checkpoints_truck_arrived; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_gtc_checkpoints_truck_arrived ON public.gtc_checkpoints USING btree (truck_id, arrived_at);


--
-- Name: ix_gts_points_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_gts_points_active ON public.gts_points USING btree (active);


--
-- Name: ix_gts_points_ward_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_gts_points_ward_id ON public.gts_points USING btree (ward_id);


--
-- Name: ix_gts_points_ward_name; Type: INDEX; Schema: public; Owner: swm
--

CREATE UNIQUE INDEX ix_gts_points_ward_name ON public.gts_points USING btree (ward_id, name);


--
-- Name: ix_operational_categories_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_operational_categories_active ON public.operational_categories USING btree (active);


--
-- Name: ix_pickup_point_crossings_crossed_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_point_crossings_crossed_at ON public.pickup_point_crossings USING btree (crossed_at);


--
-- Name: ix_pickup_point_crossings_pickup_crossed; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_point_crossings_pickup_crossed ON public.pickup_point_crossings USING btree (pickup_point_id, crossed_at);


--
-- Name: ix_pickup_point_crossings_route_crossed; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_point_crossings_route_crossed ON public.pickup_point_crossings USING btree (route_id, crossed_at);


--
-- Name: ix_pickup_point_crossings_vehicle_crossed; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_point_crossings_vehicle_crossed ON public.pickup_point_crossings USING btree (vehicle_id, crossed_at);


--
-- Name: ix_pickup_points_gts_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_points_gts_id ON public.pickup_points USING btree (gts_id);


--
-- Name: ix_pickup_points_is_gts; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_points_is_gts ON public.pickup_points USING btree (is_gts);


--
-- Name: ix_pickup_points_route_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_points_route_id ON public.pickup_points USING btree (route_id);


--
-- Name: ix_pickup_points_route_sequence; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_points_route_sequence ON public.pickup_points USING btree (route_id, sequence_no);


--
-- Name: ix_pickup_points_ward_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_points_ward_id ON public.pickup_points USING btree (ward_id);


--
-- Name: ix_pickup_points_zone_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_pickup_points_zone_id ON public.pickup_points USING btree (zone_id);


--
-- Name: ix_routes_route_type; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_routes_route_type ON public.routes USING btree (route_type);


--
-- Name: ix_routes_ward_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_routes_ward_id ON public.routes USING btree (ward_id);


--
-- Name: ix_routes_zone_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_routes_zone_id ON public.routes USING btree (zone_id);


--
-- Name: ix_secondary_vehicle_assignments_dump_yard; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_secondary_vehicle_assignments_dump_yard ON public.secondary_vehicle_assignments USING btree (dump_yard_id);


--
-- Name: ix_secondary_vehicle_assignments_gtc; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_secondary_vehicle_assignments_gtc ON public.secondary_vehicle_assignments USING btree (gtc_pickup_point_id);


--
-- Name: ix_secondary_vehicle_assignments_vehicle; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_secondary_vehicle_assignments_vehicle ON public.secondary_vehicle_assignments USING btree (vehicle_id, active);


--
-- Name: ix_system_configurations_type; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_system_configurations_type ON public.system_configurations USING btree (config_type);


--
-- Name: ix_ticket_comments_created_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_ticket_comments_created_at ON public.ticket_comments USING btree (created_at);


--
-- Name: ix_ticket_comments_ticket_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_ticket_comments_ticket_id ON public.ticket_comments USING btree (ticket_id);


--
-- Name: ix_tickets_category; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_tickets_category ON public.tickets USING btree (category);


--
-- Name: ix_tickets_created_at; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_tickets_created_at ON public.tickets USING btree (created_at);


--
-- Name: ix_tickets_priority; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_tickets_priority ON public.tickets USING btree (priority);


--
-- Name: ix_tickets_status; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_tickets_status ON public.tickets USING btree (status);


--
-- Name: ix_vehicles_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vehicles_active ON public.vehicles USING btree (active);


--
-- Name: ix_vehicles_route_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vehicles_route_id ON public.vehicles USING btree (route_id);


--
-- Name: ix_vehicles_vendor_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vehicles_vendor_id ON public.vehicles USING btree (vendor_id);


--
-- Name: ix_vehicles_ward_id; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vehicles_ward_id ON public.vehicles USING btree (ward_id);


--
-- Name: ix_vendors_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vendors_active ON public.vendors USING btree (active);


--
-- Name: ix_vendors_email; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vendors_email ON public.vendors USING btree (email);


--
-- Name: ix_vendors_vendor_name; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_vendors_vendor_name ON public.vendors USING btree (vendor_name);


--
-- Name: ix_zones_active; Type: INDEX; Schema: public; Owner: swm
--

CREATE INDEX ix_zones_active ON public.zones USING btree (active);


--
-- Name: ix_zones_code; Type: INDEX; Schema: public; Owner: swm
--

CREATE UNIQUE INDEX ix_zones_code ON public.zones USING btree (zone_code);


--
-- Name: ux_dva_active_device; Type: INDEX; Schema: public; Owner: swm
--

CREATE UNIQUE INDEX ux_dva_active_device ON public.device_vehicle_assignments USING btree (device_id) WHERE ((active IS TRUE) AND (assigned_to IS NULL));


--
-- Name: ux_dva_active_vehicle; Type: INDEX; Schema: public; Owner: swm
--

CREATE UNIQUE INDEX ux_dva_active_vehicle ON public.device_vehicle_assignments USING btree (vehicle_id) WHERE ((active IS TRUE) AND (assigned_to IS NULL));


--
-- Name: alert_actions alert_actions_alert_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.alert_actions
    ADD CONSTRAINT alert_actions_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES public.alerts(id) ON DELETE CASCADE;


--
-- Name: auth_refresh_tokens auth_refresh_tokens_replaced_by_token_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_replaced_by_token_id_fkey FOREIGN KEY (replaced_by_token_id) REFERENCES public.auth_refresh_tokens(id) ON DELETE SET NULL;


--
-- Name: auth_refresh_tokens auth_refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_refresh_tokens
    ADD CONSTRAINT auth_refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_users(id) ON DELETE CASCADE;


--
-- Name: auth_role_permissions auth_role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_role_permissions
    ADD CONSTRAINT auth_role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.auth_permissions(id) ON DELETE CASCADE;


--
-- Name: auth_role_permissions auth_role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_role_permissions
    ADD CONSTRAINT auth_role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.auth_roles(id) ON DELETE CASCADE;


--
-- Name: auth_user_roles auth_user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_user_roles
    ADD CONSTRAINT auth_user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.auth_roles(id) ON DELETE CASCADE;


--
-- Name: auth_user_roles auth_user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.auth_user_roles
    ADD CONSTRAINT auth_user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_users(id) ON DELETE CASCADE;


--
-- Name: dump_yard_weighments dump_yard_weighments_assignment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yard_weighments
    ADD CONSTRAINT dump_yard_weighments_assignment_id_fkey FOREIGN KEY (assignment_id) REFERENCES public.secondary_vehicle_assignments(id) ON DELETE SET NULL;


--
-- Name: dump_yard_weighments dump_yard_weighments_dump_yard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yard_weighments
    ADD CONSTRAINT dump_yard_weighments_dump_yard_id_fkey FOREIGN KEY (dump_yard_id) REFERENCES public.dump_yards(id) ON DELETE RESTRICT;


--
-- Name: dump_yard_weighments dump_yard_weighments_gtc_pickup_point_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yard_weighments
    ADD CONSTRAINT dump_yard_weighments_gtc_pickup_point_id_fkey FOREIGN KEY (gtc_pickup_point_id) REFERENCES public.pickup_points(id) ON DELETE SET NULL;


--
-- Name: dump_yard_weighments dump_yard_weighments_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yard_weighments
    ADD CONSTRAINT dump_yard_weighments_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id) ON DELETE RESTRICT;


--
-- Name: dump_yards dump_yards_ward_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yards
    ADD CONSTRAINT dump_yards_ward_id_fkey FOREIGN KEY (ward_id) REFERENCES public.wards(id) ON DELETE SET NULL;


--
-- Name: dump_yards dump_yards_zone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.dump_yards
    ADD CONSTRAINT dump_yards_zone_id_fkey FOREIGN KEY (zone_id) REFERENCES public.zones(id) ON DELETE SET NULL;


--
-- Name: devices fk_devices_vendor_id_vendors; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT fk_devices_vendor_id_vendors FOREIGN KEY (vendor_id) REFERENCES public.vendors(id) ON DELETE CASCADE;


--
-- Name: device_vehicle_assignments fk_dva_device_id_devices; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.device_vehicle_assignments
    ADD CONSTRAINT fk_dva_device_id_devices FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE CASCADE;


--
-- Name: device_vehicle_assignments fk_dva_vehicle_id_vehicles; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.device_vehicle_assignments
    ADD CONSTRAINT fk_dva_vehicle_id_vehicles FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id) ON DELETE CASCADE;


--
-- Name: geofences fk_geofences_route_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.geofences
    ADD CONSTRAINT fk_geofences_route_id FOREIGN KEY (route_id) REFERENCES public.routes(id) ON DELETE SET NULL;


--
-- Name: geofences fk_geofences_ward_id_wards; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.geofences
    ADD CONSTRAINT fk_geofences_ward_id_wards FOREIGN KEY (ward_id) REFERENCES public.wards(id) ON DELETE SET NULL;


--
-- Name: geofences fk_geofences_zone_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.geofences
    ADD CONSTRAINT fk_geofences_zone_id FOREIGN KEY (zone_id) REFERENCES public.zones(id) ON DELETE SET NULL;


--
-- Name: pickup_points fk_pickup_points_gts_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_points
    ADD CONSTRAINT fk_pickup_points_gts_id FOREIGN KEY (gts_id) REFERENCES public.gts_points(id) ON DELETE SET NULL;


--
-- Name: pickup_points fk_pickup_points_route_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_points
    ADD CONSTRAINT fk_pickup_points_route_id FOREIGN KEY (route_id) REFERENCES public.routes(id) ON DELETE CASCADE;


--
-- Name: pickup_points fk_pickup_points_ward_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_points
    ADD CONSTRAINT fk_pickup_points_ward_id FOREIGN KEY (ward_id) REFERENCES public.wards(id) ON DELETE RESTRICT;


--
-- Name: pickup_points fk_pickup_points_zone_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_points
    ADD CONSTRAINT fk_pickup_points_zone_id FOREIGN KEY (zone_id) REFERENCES public.zones(id) ON DELETE RESTRICT;


--
-- Name: routes fk_routes_ward_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT fk_routes_ward_id FOREIGN KEY (ward_id) REFERENCES public.wards(id) ON DELETE RESTRICT;


--
-- Name: routes fk_routes_zone_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.routes
    ADD CONSTRAINT fk_routes_zone_id FOREIGN KEY (zone_id) REFERENCES public.zones(id) ON DELETE RESTRICT;


--
-- Name: ticket_comments fk_ticket_comments_ticket_id_tickets; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.ticket_comments
    ADD CONSTRAINT fk_ticket_comments_ticket_id_tickets FOREIGN KEY (ticket_id) REFERENCES public.tickets(id) ON DELETE CASCADE;


--
-- Name: vehicles fk_vehicles_route_id_routes; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT fk_vehicles_route_id_routes FOREIGN KEY (route_id) REFERENCES public.routes(id) ON DELETE SET NULL;


--
-- Name: vehicles fk_vehicles_vendor_id_vendors; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT fk_vehicles_vendor_id_vendors FOREIGN KEY (vendor_id) REFERENCES public.vendors(id) ON DELETE RESTRICT;


--
-- Name: vehicles fk_vehicles_ward_id_wards; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT fk_vehicles_ward_id_wards FOREIGN KEY (ward_id) REFERENCES public.wards(id) ON DELETE RESTRICT;


--
-- Name: wards fk_wards_zone_id; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.wards
    ADD CONSTRAINT fk_wards_zone_id FOREIGN KEY (zone_id) REFERENCES public.zones(id) ON DELETE RESTRICT;


--
-- Name: gts_points gts_points_ward_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.gts_points
    ADD CONSTRAINT gts_points_ward_id_fkey FOREIGN KEY (ward_id) REFERENCES public.wards(id) ON DELETE SET NULL;


--
-- Name: gts_points gts_points_zone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.gts_points
    ADD CONSTRAINT gts_points_zone_id_fkey FOREIGN KEY (zone_id) REFERENCES public.zones(id) ON DELETE SET NULL;


--
-- Name: pickup_point_crossings pickup_point_crossings_pickup_point_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_point_crossings
    ADD CONSTRAINT pickup_point_crossings_pickup_point_id_fkey FOREIGN KEY (pickup_point_id) REFERENCES public.pickup_points(id) ON DELETE CASCADE;


--
-- Name: pickup_point_crossings pickup_point_crossings_route_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.pickup_point_crossings
    ADD CONSTRAINT pickup_point_crossings_route_id_fkey FOREIGN KEY (route_id) REFERENCES public.routes(id) ON DELETE SET NULL;


--
-- Name: secondary_vehicle_assignments secondary_vehicle_assignments_dump_yard_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.secondary_vehicle_assignments
    ADD CONSTRAINT secondary_vehicle_assignments_dump_yard_id_fkey FOREIGN KEY (dump_yard_id) REFERENCES public.dump_yards(id) ON DELETE RESTRICT;


--
-- Name: secondary_vehicle_assignments secondary_vehicle_assignments_gtc_pickup_point_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.secondary_vehicle_assignments
    ADD CONSTRAINT secondary_vehicle_assignments_gtc_pickup_point_id_fkey FOREIGN KEY (gtc_pickup_point_id) REFERENCES public.pickup_points(id) ON DELETE RESTRICT;


--
-- Name: secondary_vehicle_assignments secondary_vehicle_assignments_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: swm
--

ALTER TABLE ONLY public.secondary_vehicle_assignments
    ADD CONSTRAINT secondary_vehicle_assignments_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

