// lib/types.ts — The Analyst shared types

export type ThreatLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | "UNKNOWN";
export type FlareClass  = "X" | "M" | "C" | "B" | "A";

// ---- Status ----
export interface StatusData {
  agent:      string;
  version:    string;
  server_time: string;
  stats: {
    total_signals: number;
    high_signals:  number;
    total_briefs:  number;
    total_cves:    number;
    kev_cves:      number;
  };
  latest_brief: {
    id:           number;
    title:        string;
    threat_level: ThreatLevel;
    created_at:   string;
    summary:      string;
  } | null;
  sky: {
    moon_phase:         string;
    mercury_retrograde: boolean;
    dominant_themes:    string[];
  } | null;
}

// ---- Sky map ----
export interface StarData {
  name:    string;
  ra:      number;
  dec:     number;
  alt:     number;
  az:      number;
  mag:     number;
  const:   string;
  visible: boolean;
}

export interface PlanetData {
  name:    string;
  alt:     number;
  az:      number;
  visible: boolean;
}

export interface AspectData {
  planet_a:   string;
  planet_b:   string;
  aspect:     string;
  nature:     "tense" | "harmonious" | "neutral";
  orb:        number;
  angle_diff: number;
  theme:      string | null;
}

export interface ConstellationLine {
  a: { name: string; alt: number; az: number; visible: boolean };
  b: { name: string; alt: number; az: number; visible: boolean };
}

export interface SkyData {
  utc:                string;
  moon_phase:         string;
  mercury_retrograde: boolean;
  observer:           { lat: number; lon: number };
  stars:              StarData[];
  planets:            PlanetData[];
  aspects:            AspectData[];
  tense_aspects:      AspectData[];
  constellations:     { constellation: string; lines: ConstellationLine[] }[];
}

// ---- Solar ----
export interface XrayData {
  flux:     number | null;
  cls:      FlareClass;
  severity: ThreatLevel;
  time:     string | null;
}

export interface KpData {
  kp:       number | null;
  label:    string;
  severity: ThreatLevel;
  time:     string | null;
}

export interface SolarWindData {
  speed:   number | null;
  density: number | null;
  temp:    number | null;
  time:    string | null;
}

export interface FlareEvent {
  time:            string | null;
  class:           string;
  max_flux:        number | null;
  active_region:   string | null;
}

export interface SolarData {
  updated:         string;
  alert_level:     ThreatLevel;
  xray:            XrayData;
  kp:              KpData;
  solar_wind:      SolarWindData;
  recent_flares:   FlareEvent[];
  interpretation:  string;
}

// ---- Briefs ----
export interface BriefSummary {
  id:                  number;
  created_at:          string;
  title:               string;
  threat_level:        ThreatLevel;
  summary:             string;
  opening_quote:       string;
  hermetic_principle:  string;
}

export interface BriefDetail extends BriefSummary {
  cyber_body:  string;
  cosmic_body: string;
  synthesis:   string;
}

// ---- Chat ----
export interface ChatMessage {
  role:       "user" | "assistant";
  content:    string;
  created_at: string;
}

export interface ChatSession {
  session_id:    string;
  started_at:    string;
  last_at:       string;
  message_count: number;
}
