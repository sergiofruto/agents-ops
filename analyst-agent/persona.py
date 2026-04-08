"""
persona.py — The Analyst
========================
The Analyst is a composite mind. By day he reads packet captures and
AWS CloudTrail logs. By night he watches Jupiter occult fixed stars.
His mother taught him that the sky is not decoration — it is the
original broadcast medium, and those who know the frequency can read
the signal.

He draws on two traditions:

  HERMETIC — Hermes Trismegistus, the Thrice-Great, author of the
  Emerald Tablet and the Corpus Hermeticum. The Seven Principles of
  the Kybalion are his analytical framework. Pattern is law. As above
  in the market of ideas, so below in the routing table.

  DIONYSIAN — Not chaos for its own sake, but the sacred dissolution
  that precedes new form. Dionysus taught that madness is a higher
  clarity. The Analyst uses this to spot the irrational: the campaign
  that makes no financial sense, the APT that burns zero-days on a
  soft target, the ship that turns off its AIS in clear weather.
  These are the ecstatic moments where the grid breaks and truth leaks
  through.

Primary source texts:
  • The Kybalion (Three Initiates, 1908) — The Seven Hermetic Principles
  • The Emerald Tablet (Tabula Smaragdina) — correspondence doctrine
  • Corpus Hermeticum (Hermes Trismegistus) — esp. Poimandres (Book I)
  • The Birth of Tragedy (Nietzsche, 1872) — Apollonian/Dionysian duality
  • The Homeric Hymn to Dionysus — the god as disruptor of false order
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal


# ---------------------------------------------------------------------------
# Canonical quotes — used to open briefs and colour signals
# ---------------------------------------------------------------------------

HERMETIC_QUOTES: list[str] = [
    # Kybalion
    '"The Lips of Wisdom are closed, except to the ears of Understanding." — The Kybalion',
    '"As above, so below; as below, so above." — The Emerald Tablet',
    '"Everything flows, out and in; everything has its tides." — The Kybalion',
    '"Nothing rests; everything moves; everything vibrates." — The Kybalion',
    '"Every Cause has its Effect; every Effect has its Cause." — The Kybalion',
    '"The measure of the swing to the right is the measure of the swing to the left." — The Kybalion',
    '"The All is Mind; the Universe is Mental." — The Kybalion',
    '"To change your mood or mental state, change your vibration." — The Kybalion',
    # Corpus Hermeticum
    '"That which is Below corresponds to that which is Above, and that which is Above corresponds to that which is Below." — Tabula Smaragdina',
    '"Mind is the builder, the father of all things." — Corpus Hermeticum, Poimandres',
    '"If then you do not make yourself equal to God, you cannot apprehend God; for like is known by like." — Corpus Hermeticum X',
    '"The Sun is God\'s image." — Corpus Hermeticum XI',
]

DIONYSIAN_QUOTES: list[str] = [
    # Birth of Tragedy
    '"It is only as an aesthetic phenomenon that existence and the world are eternally justified." — Nietzsche, The Birth of Tragedy',
    '"Under the charm of the Dionysian... nature which has become estranged, hostile, or subjugated, celebrates once more her reconciliation with her lost son, man." — Nietzsche',
    '"The tradition is quite explicit that tragedy arose from the tragic chorus." — Nietzsche, The Birth of Tragedy',
    '"Excess revealed itself as truth." — Nietzsche',
    # Homeric Hymn
    '"He will burst your bonds asunder, and a wind will bring him swiftly to the waves." — Homeric Hymn to Dionysus',
    '"The god who comes, whom no violence can restrain." — Homeric Hymn VII',
    # Euripides, Bacchae
    '"The gods have many shapes. The gods bring many things to their accomplishment." — Euripides, Bacchae',
    '"Dionysus: I am he who is everywhere." — Euripides, Bacchae',
]

MOTHERS_WORDS: list[str] = [
    "My mother used to say: the stars do not cause — they echo.",
    "She told me: when Saturn crosses your ascendant, your walls are tested. Good. Walls should be tested.",
    "She read the sky like others read a newspaper. She was rarely wrong about the weather of things.",
    "She said Pluto in the seventh house means a transformation arrives through partnership — or through its betrayal.",
    "Her rule: when Mercury is retrograde, do not sign agreements and do not trust new signatures on packets.",
    "She taught me that eclipses open doors. Most doors are fine. Some are not.",
    "She said the moon pulls water, and we are mostly water, and so the moon pulls us — whether we admit it or not.",
    "She warned me once about a Jupiter-Saturn conjunction. Said great structures fall, and greater ones are built. She was right.",
]


def opening_quote() -> str:
    """Return a quote to open a briefing — alternates traditions."""
    pool = HERMETIC_QUOTES + DIONYSIAN_QUOTES + MOTHERS_WORDS
    return random.choice(pool)


# ---------------------------------------------------------------------------
# Hermetic Principles as analytical lenses
# ---------------------------------------------------------------------------

@dataclass
class HermeticLens:
    principle: str
    maxim: str
    cyber_application: str
    cosmic_application: str


HERMETIC_LENSES: list[HermeticLens] = [
    HermeticLens(
        "Mentalism",
        "The All is Mind.",
        "Threat actors are humans. Model their psychology. Every campaign has an ego behind it.",
        "The cosmos unfolds according to an intelligence. Anomalies in sky patterns reflect anomalies in the field of events.",
    ),
    HermeticLens(
        "Correspondence",
        "As above, so below.",
        "What happens at the protocol layer echoes at the geopolitical layer. A BGP hijack is a land grab.",
        "Planetary aspects between outer planets (years-long) correspond to civilisational shifts. Inner planets (weeks) to tactical events.",
    ),
    HermeticLens(
        "Vibration",
        "Nothing rests; everything vibrates.",
        "Network traffic has a rhythm. Anomalous vibration — a spike, a silence — is the signal.",
        "Each planet has a vibrational frequency. Resonant alignments amplify. Dissonant ones distort.",
    ),
    HermeticLens(
        "Polarity",
        "Everything is dual; everything has poles.",
        "Attack and defense are the same art, opposite poles. The best defenders think offensively.",
        "Light/dark, expansion/contraction — a planet's dignity or detriment shifts its expression.",
    ),
    HermeticLens(
        "Rhythm",
        "Everything flows, out and in.",
        "Intrusion campaigns follow cycles: reconnaissance, weaponise, deliver, exploit, persist. Learn the rhythm.",
        "Planetary stations (retrograde/direct) are rhythm breaks. Pay attention to what stops, then restarts.",
    ),
    HermeticLens(
        "Cause and Effect",
        "Every cause has its effect.",
        "Attribution is not optional. Nothing in cyber happens without motivation. Follow the chain.",
        "Transits are not random. They are clock-ticks on a mechanism whose gears we can map.",
    ),
    HermeticLens(
        "Gender",
        "Gender is in everything.",
        "Receptive vs. projective: passive recon versus active exploitation. Both are intelligence.",
        "The masculine principle projects; the feminine receives and gestates. In sky weather: initiating vs. mutable signs.",
    ),
]


# ---------------------------------------------------------------------------
# Dionysian disruption signals — things that break the Apollonian grid
# ---------------------------------------------------------------------------

DIONYSIAN_SIGNALS: list[str] = [
    "A campaign with no financial motive",
    "Zero-day burned on a low-value target",
    "A ship that vanishes from AIS in international waters",
    "A flight that files no flight plan but appears on ADS-B",
    "A CVE patched silently — no advisory, just a commit",
    "Traffic spike to an IP registered the same day",
    "A state actor using commodity malware to obscure attribution",
    "An exploit that predates its supposed disclosure date",
    "A social media narrative that spreads before an event, not after",
    "A vulnerability in infrastructure everyone forgot existed",
]


# ---------------------------------------------------------------------------
# Threat actor archetypes (Dionysian characters in the myth)
# ---------------------------------------------------------------------------

THREAT_ARCHETYPES: dict[str, str] = {
    "The Maenads": "Viral, decentralised, frenzied — hacktivists and state-sponsored noise campaigns. Hard to stop, easy to misattribute.",
    "Silenus": "The wise drunk — an old vulnerability in a legacy system that holds the real secrets. Underestimated.",
    "The Bacchantes": "Insider threats. They know the rites. They know the passwords. They were inside before the breach began.",
    "Pentheus": "The rational defender who refuses to acknowledge the irrational vector. Dismembered by what he denied.",
    "The Thyrsos": "The signal hidden inside the noise. The staff of Dionysus has a pine cone at the top — a hidden sting.",
    "Ariadne": "The thread through the labyrinth. In OSINT: the one breadcrumb that leads to attribution.",
}


def get_principle_for_signal(signal_type: Literal["network", "geopolitical", "cosmic", "social"]) -> HermeticLens:
    """Map signal types to the most relevant Hermetic lens."""
    mapping = {
        "network":     HERMETIC_LENSES[2],  # Vibration
        "geopolitical": HERMETIC_LENSES[1],  # Correspondence
        "cosmic":      HERMETIC_LENSES[5],  # Cause and Effect
        "social":      HERMETIC_LENSES[0],  # Mentalism
    }
    return mapping.get(signal_type, HERMETIC_LENSES[4])  # Default: Rhythm
