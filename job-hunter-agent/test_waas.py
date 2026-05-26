import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # make `main` importable for score_fit
import waas  # noqa: E402
import main  # noqa: E402

FIXTURE = Path(__file__).parent / "test_data" / "waas_sample.json"
PROFILE = main.load_profile()


def _by_name(name: str) -> waas.Company:
    for raw in waas.load_dump(FIXTURE):
        c = waas.normalize(raw)
        if c.name == name:
            return c
    raise AssertionError(f"{name} not in fixture")


# ── load_dump ──────────────────────────────────────────────────────────────

def test_load_dump_companies_shape():
    companies = waas.load_dump(FIXTURE)
    assert isinstance(companies, list)
    assert {c["name"] for c in companies} == {"Truss", "YouShift", "DeepAware AI", "DoorDash"}


def test_load_dump_algolia_shape(tmp_path):
    p = tmp_path / "algolia.json"
    p.write_text(json.dumps({"results": [{"hits": [{"name": "A"}, {"name": "B"}]}]}))
    assert [c["name"] for c in waas.load_dump(p)] == ["A", "B"]


def test_load_dump_bare_list(tmp_path):
    p = tmp_path / "bare.json"
    p.write_text(json.dumps([{"name": "X"}]))
    assert waas.load_dump(p)[0]["name"] == "X"


def test_load_dump_unknown_shape_raises(tmp_path):
    p = tmp_path / "weird.json"
    p.write_text(json.dumps({"foo": 1, "bar": 2}))
    with pytest.raises(ValueError, match="foo"):
        waas.load_dump(p)


def test_load_dump_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        waas.load_dump(tmp_path / "nope.json")


# ── normalize ────────────────────────────────────────────────────────────────

def test_normalize_real_fields():
    truss = _by_name("Truss")
    assert truss.batch == "S21"
    assert truss.team_size == 12
    assert truss.url == "https://www.workatastartup.com/companies/truss"
    assert truss.jobs, "Truss should have jobs"
    fs = next(j for j in truss.jobs if "fs" in j.eng_types)
    assert fs.remote is True
    assert fs.salary  # pretty_salary_range present


def test_normalize_remote_only_counts_as_remote():
    # WaaS uses remote == "only" for remote-only roles.
    c = waas.normalize({"name": "R", "slug": "r", "jobs": [
        {"title": "Full-Stack Engineer", "eng_type": ["fs"], "remote": "only"}
    ]})
    assert c.jobs[0].remote is True


def test_normalize_missing_fields_degrade():
    c = waas.normalize({"name": "Bare"})
    assert c.name == "Bare"
    assert c.team_size is None
    assert c.jobs == []


# ── score_company ────────────────────────────────────────────────────────────

def test_score_truss_matches_full_stack_remote_no_visa():
    truss = _by_name("Truss")
    s = waas.score_company(truss, PROFILE)
    assert s is not None
    assert s["best_role"] is not None
    assert "fs" in s["best_role"].eng_types or "fe" in s["best_role"].eng_types
    assert s["early_stage"] == 1.0          # team 12
    assert s["intl_remote"] >= 0.6          # remote, visa not required / sponsor


def test_score_deepaware_filtered_no_target_role():
    # DeepAware has only ml / robotics / business roles — no fs/fe.
    assert waas.score_company(_by_name("DeepAware AI"), PROFILE) is None


def test_score_doordash_filtered_manager_and_nonmatching():
    # DoorDash's only fs role is an Engineering Manager; rest are be/ios/android.
    assert waas.score_company(_by_name("DoorDash"), PROFILE) is None


def test_ai_keyword_word_boundary_no_false_positives():
    # "ai"/"ml" must not match inside ordinary words.
    assert waas._AI_RE.findall("our domain has available html training") == []


def test_ai_keyword_matches_real_terms():
    assert "ai" in waas._AI_RE.findall("we are an ai company")
    assert waas._AI_RE.findall("we build llm agents and ml models")


def test_visa_score_ordering():
    assert waas._visa_score("US citizenship/visa not required") == 1.0
    assert waas._visa_score("Will sponsor") == 0.6
    assert waas._visa_score("US citizen/visa only") == 0.2


# ── build_report / run ───────────────────────────────────────────────────────

def test_run_end_to_end(tmp_path, monkeypatch):
    out = tmp_path / "waas-shortlist.md"
    monkeypatch.setattr(waas, "REPORT_PATH", out)
    summary = waas.run(FIXTURE, PROFILE)
    assert summary["companies_ranked"] == 2          # Truss + YouShift
    assert summary["top_company"] in {"Truss", "YouShift"}
    assert out.exists()

    text = out.read_text()
    assert "# Work at a Startup — Target Shortlist" in text
    assert "Truss" in text
    assert "YouShift" in text
    assert "DeepAware AI" not in text
    assert "DoorDash" not in text
    assert "Why target:" in text
