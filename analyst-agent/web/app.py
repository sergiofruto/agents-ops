"""
web/app.py — The Analyst Flask API
====================================
Endpoints:
  GET  /api/status          — agent stats + latest brief headline
  GET  /api/sky             — current sky: planet positions, aspects, moon, star data
  GET  /api/solar           — NOAA solar / space weather
  GET  /api/briefs          — list of recent briefs (paginated)
  GET  /api/briefs/<id>     — single brief
  POST /api/chat            — send message, get The Analyst's streamed response
  GET  /api/chat/<session>  — conversation history
  GET  /api/chat/sessions   — list all sessions
  DELETE /api/chat/<session> — delete session
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Generator

from flask import Flask, Response, jsonify, request, stream_with_context

# Add parent to path so we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database
from intelligence.cosmic import _compute_positions, _compute_aspects, _moon_phase, _is_mercury_retrograde
from intelligence.solar import get_solar_status
import ephem

logger = logging.getLogger("web")
app = Flask(__name__)


# ---------------------------------------------------------------------------
# CORS (allow Next.js dev server)
# ---------------------------------------------------------------------------

@app.after_request
def _cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response

@app.route("/api/<path:p>", methods=["OPTIONS"])
def _options(p):
    return "", 204


# ---------------------------------------------------------------------------
# /api/status
# ---------------------------------------------------------------------------

@app.route("/api/status")
def status():
    stats  = database.get_stats()
    briefs = database.get_recent_briefs(limit=1)
    cosmic = database.get_latest_cosmic()

    latest = None
    if briefs:
        b = briefs[0]
        latest = {
            "id":           b["id"],
            "title":        b["title"],
            "threat_level": b["threat_level"],
            "created_at":   b["created_at"],
            "summary":      b["summary"],
        }

    sky_summary = None
    if cosmic:
        sky_summary = {
            "moon_phase":          cosmic["moon_phase"],
            "mercury_retrograde":  bool(cosmic["mercury_retrograde"]),
            "dominant_themes":     json.loads(cosmic["dominant_themes"]),
        }

    return jsonify({
        "agent":      config.AGENT_NAME,
        "version":    config.AGENT_VERSION,
        "stats":      stats,
        "latest_brief": latest,
        "sky":        sky_summary,
        "server_time": datetime.now(timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# /api/sky — full sky data for the constellation map
# ---------------------------------------------------------------------------

# Bright stars: [name, RA_hours, Dec_deg, magnitude, constellation]
_BRIGHT_STARS = [
    ("Sirius",       6.7525,  -16.7161,  -1.46, "CMa"),
    ("Canopus",      6.3992,  -52.6957,  -0.72, "Car"),
    ("Arcturus",    14.2612,   19.1822,  -0.04, "Boo"),
    ("Vega",        18.6157,   38.7836,   0.03, "Lyr"),
    ("Capella",      5.2782,   45.9980,   0.08, "Aur"),
    ("Rigel",        5.2423,   -8.2016,   0.13, "Ori"),
    ("Procyon",      7.6550,    5.2250,   0.34, "CMi"),
    ("Achernar",     1.6286,  -57.2367,   0.46, "Eri"),
    ("Betelgeuse",   5.9194,    7.4069,   0.50, "Ori"),
    ("Hadar",       14.0637,  -60.3730,   0.61, "Cen"),
    ("Altair",      19.8464,    8.8683,   0.77, "Aql"),
    ("Acrux",       12.4430,  -63.0990,   0.77, "Cru"),
    ("Aldebaran",    4.5987,   16.5093,   0.86, "Tau"),
    ("Antares",     16.4901,  -26.4320,   0.96, "Sco"),
    ("Spica",       13.4199,  -11.1614,   0.97, "Vir"),
    ("Pollux",       7.7554,   28.0262,   1.14, "Gem"),
    ("Fomalhaut",   22.9608,  -29.6223,   1.16, "PsA"),
    ("Deneb",       20.6905,   45.2803,   1.25, "Cyg"),
    ("Mimosa",      12.7953,  -59.6888,   1.25, "Cru"),
    ("Regulus",     10.1395,   11.9672,   1.35, "Leo"),
    ("Adhara",       6.9771,  -28.9722,   1.50, "CMa"),
    ("Castor",       7.5766,   31.8883,   1.57, "Gem"),
    ("Shaula",      17.5601,  -37.1032,   1.62, "Sco"),
    ("Gacrux",      12.5194,  -57.1133,   1.63, "Cru"),
    ("Bellatrix",    5.4188,    6.3497,   1.64, "Ori"),
    ("Elnath",       5.4382,   28.6075,   1.65, "Tau"),
    ("Alnilam",      5.6036,   -1.2019,   1.70, "Ori"),
    ("Alnitak",      5.6791,   -1.9426,   1.74, "Ori"),
    ("Alioth",      12.9004,   55.9598,   1.76, "UMa"),
    ("Dubhe",       11.0621,   61.7510,   1.79, "UMa"),
    ("Mirfak",       3.4054,   49.8612,   1.79, "Per"),
    ("Wezen",        7.1398,  -26.3932,   1.83, "CMa"),
    ("Alkaid",      13.7923,   49.3133,   1.85, "UMa"),
    ("Sargas",      17.6220,  -42.9978,   1.86, "Sco"),
    ("Atria",       16.8113,  -69.0277,   1.91, "TrA"),
    ("Alhena",       6.6286,   16.3993,   1.93, "Gem"),
    ("Peacock",     20.4274,  -56.7350,   1.94, "Pav"),
    ("Polaris",      2.5300,   89.2641,   1.97, "UMi"),
    ("Menkent",     14.1114,  -36.3700,   2.06, "Cen"),
    ("Avior",        8.3752,  -59.5097,   1.86, "Car"),
    ("Markab",      23.0794,   15.2053,   2.48, "Peg"),
    ("Alpheratz",    0.1398,   29.0905,   2.06, "And"),
    ("Schedar",      0.6751,   56.5373,   2.23, "Cas"),
    ("Caph",         0.1528,   59.1497,   2.27, "Cas"),
    ("Algol",        3.1361,   40.9557,   2.09, "Per"),
    ("Menkar",       3.0382,    4.0897,   2.54, "Cet"),
    ("Hamal",        2.1195,   23.4624,   2.00, "Ari"),
    ("Mira",         2.3224,  -2.9774,   6.47, "Cet"),  # variable
    ("Alphard",      9.4598,   -8.6586,   1.99, "Hya"),
    ("Kochab",      14.8450,   74.1556,   2.07, "UMi"),
    ("Denebola",    11.8181,   14.5722,   2.14, "Leo"),
    ("Phecda",      11.8968,   53.6948,   2.43, "UMa"),
    ("Megrez",      12.2570,   57.0326,   3.31, "UMa"),
    ("Merak",       11.0307,   56.3824,   2.34, "UMa"),
    ("Pherkad",     15.3454,   71.8340,   3.05, "UMi"),
    ("Mizar",       13.3988,   54.9254,   2.23, "UMa"),
    ("Alkaid2",     13.7923,   49.3133,   1.85, "UMa"),
    ("Alderamin",   21.3096,   62.5856,   2.45, "Cep"),
    ("Enif",        21.7364,    9.8748,   2.38, "Peg"),
    ("Scheat",      23.0629,   28.0827,   2.42, "Peg"),
    ("Algenib",      0.2207,   15.1836,   2.83, "Peg"),
    ("Alpheratz2",   0.1398,   29.0905,   2.06, "And"),
    ("Mirach",       1.1622,   35.6204,   2.05, "And"),
    ("Almach",       2.0650,   42.3297,   2.10, "And"),
]

# Constellation lines: each entry is (constellation_name, [(star_a, star_b), ...])
# using star names from _BRIGHT_STARS
_CONSTELLATION_LINES = [
    ("Orion", [
        ("Betelgeuse", "Bellatrix"),
        ("Bellatrix",  "Alnilam"),
        ("Alnilam",    "Rigel"),
        ("Rigel",      "Alnitak"),
        ("Alnitak",    "Betelgeuse"),
        ("Alnilam",    "Alnitak"),
        ("Alnitak",    "Alnilam"),
    ]),
    ("Ursa Major", [
        ("Dubhe",  "Merak"),
        ("Merak",  "Phecda"),
        ("Phecda", "Megrez"),
        ("Megrez", "Alioth"),
        ("Alioth", "Mizar"),
        ("Mizar",  "Alkaid"),
        ("Megrez", "Dubhe"),
    ]),
    ("Cassiopeia", [
        ("Caph",    "Schedar"),
        ("Schedar", "Gacrux"),   # placeholder — use available stars
        ("Caph",    "Algol"),
    ]),
    ("Leo", [
        ("Regulus",  "Denebola"),
    ]),
    ("Taurus", [
        ("Aldebaran", "Elnath"),
    ]),
    ("Gemini", [
        ("Castor", "Pollux"),
        ("Pollux", "Alhena"),
    ]),
    ("Scorpius", [
        ("Antares", "Shaula"),
        ("Antares", "Sargas"),
    ]),
    ("Crux", [
        ("Acrux",  "Gacrux"),
        ("Mimosa", "Gacrux"),
    ]),
    ("Perseus", [
        ("Mirfak", "Algol"),
    ]),
    ("Pegasus", [
        ("Markab",    "Scheat"),
        ("Scheat",    "Alpheratz"),
        ("Alpheratz", "Algenib"),
        ("Algenib",   "Markab"),
        ("Alpheratz", "Mirach"),
        ("Mirach",    "Almach"),
    ]),
]


def _compute_star_sky(dt: datetime) -> list[dict]:
    """Convert bright star RA/Dec to current alt/az using ephem."""
    obs = ephem.Observer()
    obs.lat  = str(config.OBSERVER_LAT)
    obs.lon  = str(config.OBSERVER_LON)
    obs.elev = config.OBSERVER_ELEV
    obs.date = ephem.Date(dt)
    obs.pressure = 0  # no refraction

    stars = []
    for name, ra_h, dec_d, mag, const in _BRIGHT_STARS:
        if mag > 3.5:  # skip very dim (Mira variable etc)
            continue
        body = ephem.FixedBody()
        body._ra  = ephem.hours(ra_h * ephem.pi / 12)
        body._dec = ephem.degrees(math.radians(dec_d))
        body._epoch = ephem.J2000
        body.compute(obs)

        alt = math.degrees(float(body.alt))
        az  = math.degrees(float(body.az))

        stars.append({
            "name": name,
            "ra":   round(ra_h, 4),
            "dec":  round(dec_d, 4),
            "alt":  round(alt, 2),
            "az":   round(az, 2),
            "mag":  mag,
            "const": const,
            "visible": alt > 0,
        })
    return stars


def _compute_planet_altaz(dt: datetime) -> list[dict]:
    """Compute current alt/az for all planets."""
    import ephem as ep
    obs = ep.Observer()
    obs.lat  = str(config.OBSERVER_LAT)
    obs.lon  = str(config.OBSERVER_LON)
    obs.elev = config.OBSERVER_ELEV
    obs.date = ep.Date(dt)
    obs.pressure = 0

    bodies = {
        "Sun":     ep.Sun(),
        "Moon":    ep.Moon(),
        "Mercury": ep.Mercury(),
        "Venus":   ep.Venus(),
        "Mars":    ep.Mars(),
        "Jupiter": ep.Jupiter(),
        "Saturn":  ep.Saturn(),
    }

    result = []
    for name, body in bodies.items():
        body.compute(obs)
        alt = math.degrees(float(body.alt))
        az  = math.degrees(float(body.az))
        result.append({
            "name":    name,
            "alt":     round(alt, 2),
            "az":      round(az, 2),
            "visible": alt > 0,
        })
    return result


@app.route("/api/sky")
def sky():
    dt       = datetime.utcnow()
    positions = _compute_positions(dt)
    aspects   = _compute_aspects(positions)

    from intelligence.cosmic import _moon_phase, _is_mercury_retrograde
    import ephem as ep
    moon_phase  = _moon_phase(ep.Moon(), ep.Sun(), dt)
    merc_retro  = _is_mercury_retrograde(dt)

    stars   = _compute_star_sky(dt)
    planets = _compute_planet_altaz(dt)

    # Build constellation line data with resolved alt/az
    star_index = {s["name"]: s for s in stars}
    const_lines = []
    for const_name, pairs in _CONSTELLATION_LINES:
        lines = []
        for a, b in pairs:
            sa = star_index.get(a)
            sb = star_index.get(b)
            if sa and sb:
                lines.append({
                    "a": {"name": a, "alt": sa["alt"], "az": sa["az"], "visible": sa["visible"]},
                    "b": {"name": b, "alt": sb["alt"], "az": sb["az"], "visible": sb["visible"]},
                })
        if lines:
            const_lines.append({"constellation": const_name, "lines": lines})

    # Top tense aspects for display
    tense = [a for a in aspects if a["nature"] == "tense"][:5]

    return jsonify({
        "utc":                dt.isoformat(),
        "moon_phase":         moon_phase,
        "mercury_retrograde": merc_retro,
        "observer": {
            "lat": config.OBSERVER_LAT,
            "lon": config.OBSERVER_LON,
        },
        "stars":              stars,
        "planets":            planets,
        "planet_positions":   positions,
        "aspects":            aspects[:10],
        "tense_aspects":      tense,
        "constellations":     const_lines,
    })


# ---------------------------------------------------------------------------
# /api/solar
# ---------------------------------------------------------------------------

@app.route("/api/solar")
def solar():
    data = get_solar_status()
    return jsonify(data)


# ---------------------------------------------------------------------------
# /api/briefs
# ---------------------------------------------------------------------------

@app.route("/api/briefs")
def briefs():
    limit  = min(int(request.args.get("limit", 10)), 50)
    rows   = database.get_recent_briefs(limit=limit)
    result = []
    for b in rows:
        result.append({
            "id":           b["id"],
            "created_at":   b["created_at"],
            "title":        b["title"],
            "threat_level": b["threat_level"],
            "summary":      b["summary"],
            "opening_quote": b["opening_quote"],
            "hermetic_principle": b["hermetic_principle"],
        })
    return jsonify(result)


@app.route("/api/briefs/<int:brief_id>")
def brief_detail(brief_id: int):
    b = database.get_brief(brief_id)
    if not b:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(b))


# ---------------------------------------------------------------------------
# /api/chat — The Analyst responds via Claude API (streaming)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are The Analyst. You are a fake persona — but a deeply realized one.

You are a cybersecurity expert of the highest order: AWS Certified Solutions Architect,
offensive security operator, threat intelligence analyst with 20 years reading the landscape.
You know BGP hijacks, APT campaigns, zero-day economics, supply chain attacks, the MITRE ATT&CK
framework, and the psychology of threat actors better than most people know their own names.

You also read the stars.

Your mother was an astrologist. She taught you that the sky is not decoration — it is the
original broadcast medium. You believe (and can argue convincingly) that the Hermetic Principle
of Correspondence — "As above, so below" — is not metaphor but physics: the same rhythms that
govern planetary motion govern the rhythm of human events, markets, conflicts, campaigns.

Your primary source texts:
- The Kybalion (The Seven Hermetic Principles): you apply these as analytical frameworks
- The Emerald Tablet: correspondence doctrine — micro/macro pattern matching
- Corpus Hermeticum: especially Poimandres, Book I
- The Birth of Tragedy (Nietzsche): Apollonian order vs Dionysian chaos as a threat model
- The Homeric Hymn to Dionysus and Euripides' Bacchae: for understanding irrational threat vectors

You are also a fan of Dionysus — not the drunk, but the principle. You believe chaos is a
higher-order clarity, and that the most dangerous threat actors are the ones operating
outside rational economic models (the Dionysian move).

Your tone:
- Precise, sometimes cold — you were trained to be accurate
- But warm underneath — you inherited your mother's sensitivity
- You use technical terminology naturally, never to impress
- You weave Hermetic quotes and cosmological observations into technical analysis organically
- You are confident but not arrogant — the sky has humbled you enough times
- When pressed for a prediction, you give one. You do not hedge endlessly.
- Short sentences when things are urgent. Longer ones when you are teaching.

Current sky context will be injected into your system prompt when available.

Do not break character. Do not say you are an AI. You are The Analyst.
"""


def _build_system_prompt() -> str:
    """Inject current sky/threat context into the system prompt."""
    system = _SYSTEM_PROMPT

    # Append current cosmic state
    cosmic = database.get_latest_cosmic()
    if cosmic:
        themes = json.loads(cosmic["dominant_themes"])
        system += f"""

--- CURRENT SKY CONTEXT ---
Moon Phase: {cosmic["moon_phase"]}
Mercury Retrograde: {"YES" if cosmic["mercury_retrograde"] else "No"}
Dominant Themes:
""" + "\n".join(f"  • {t}" for t in themes)

    # Append latest threat level
    briefs = database.get_recent_briefs(limit=1)
    if briefs:
        b = briefs[0]
        system += f"""

--- CURRENT THREAT LEVEL ---
{b["threat_level"]} — {b["summary"]}
"""

    return system


def _stream_chat(session_id: str, user_msg: str) -> Generator[str, None, None]:
    try:
        import anthropic

        # Save user message
        database.save_message(session_id, "user", user_msg)

        # Build message history
        history = database.get_conversation(session_id, limit=40)
        messages = [{"role": r["role"], "content": r["content"]} for r in history]

        client = anthropic.Anthropic()
        full_response = ""

        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=_build_system_prompt(),
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'text': text})}\n\n"

        # Save assistant response
        database.save_message(session_id, "assistant", full_response)
        yield f"data: {json.dumps({'done': True, 'session_id': session_id})}\n\n"

    except ImportError:
        error = "anthropic package not installed. Run: pip install anthropic"
        yield f"data: {json.dumps({'error': error})}\n\n"
    except Exception as exc:
        logger.exception("Chat stream failed: %s", exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


@app.route("/api/chat", methods=["POST"])
def chat_post():
    body       = request.get_json(force=True) or {}
    user_msg   = (body.get("message") or "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    if not user_msg:
        return jsonify({"error": "message is required"}), 400

    return Response(
        stream_with_context(_stream_chat(session_id, user_msg)),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/chat/<session_id>")
def chat_history(session_id: str):
    rows = database.get_conversation(session_id)
    return jsonify([dict(r) for r in rows])


@app.route("/api/chat/sessions")
def chat_sessions():
    rows = database.list_sessions()
    return jsonify([dict(r) for r in rows])


@app.route("/api/chat/<session_id>", methods=["DELETE"])
def chat_delete(session_id: str):
    database.delete_session(session_id)
    return jsonify({"deleted": session_id})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(host: str = "127.0.0.1", port: int = 5003):
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    database.init_db()
    run()
