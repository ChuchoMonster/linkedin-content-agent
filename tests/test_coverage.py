"""coverage.py: the ledger that stops the daily run repeating a story."""
import argparse
import datetime
import json
import sys

import pytest

import coverage


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "coverage.json"
    monkeypatch.setattr(coverage, "LEDGER", path)
    return path


def days_ago(n):
    return (datetime.date.fromisoformat(coverage.today()) - datetime.timedelta(days=n)).isoformat()


def seed(path, *entries):
    path.write_text(json.dumps({"entries": list(entries)}))


def entry(date, headline, entities, slug="s", angle="an angle"):
    return {"date": date, "slug": slug, "headline": headline, "entities": entities,
            "angle": angle, "format": "text", "permalink": ""}


def check(text, days=7):
    return coverage.cmd_check(argparse.Namespace(text=text, days=days))


# --- similarity ---------------------------------------------------------------

def test_tokens_drop_stopwords_and_short_words_and_keep_amounts():
    assert coverage.tokens("The Nvidia deal is $105B for an Ohio data center") == {
        "nvidia", "deal", "$105b", "ohio", "data", "center"}


def test_single_shared_big_name_is_not_a_duplicate():
    # Without the floor of 4 this would score 100% and block every story about OpenAI.
    assert coverage.overlap("OpenAI", "OpenAI launches a browser for schools") == 0.25


# --- check ------------------------------------------------------------------

def test_same_story_is_flagged_with_the_angle_already_used(ledger, capsys):
    seed(ledger, entry(days_ago(1), "Nvidia backs $105B for OpenAI Ohio data center",
                       ["Nvidia", "OpenAI", "SoftBank"], angle="vendor financing"))
    assert check("Nvidia financing OpenAI Ohio data center deal") == 1
    out = capsys.readouterr().out
    assert out.startswith("OVERLAP -- 1 prior post(s)")
    assert "angle already used: vendor financing" in out


def test_match_on_entities_alone_counts(ledger):
    seed(ledger, entry(days_ago(2), "Payments giant buys a model router",
                       ["Stripe", "OpenRouter"]))
    assert check("Stripe OpenRouter acquisition closes") == 1


def test_unrelated_story_is_clear(ledger, capsys):
    seed(ledger, entry(days_ago(1), "Micron posted an 87% gross margin on memory chips", ["Micron"]))
    assert check("Etched raises $700M for inference chips") == 0
    assert capsys.readouterr().out.startswith("CLEAR")


def test_story_older_than_window_is_ignored(ledger):
    seed(ledger, entry(days_ago(8), "Nvidia backs $105B for OpenAI Ohio data center",
                       ["Nvidia", "OpenAI"]))
    assert check("Nvidia backs $105B for OpenAI Ohio data center", days=7) == 0
    assert check("Nvidia backs $105B for OpenAI Ohio data center", days=10) == 1


def test_cli_check_exits_nonzero_on_overlap(ledger, monkeypatch):
    seed(ledger, entry(days_ago(0), "Etched raised $700M at $21B", ["Etched"]))
    monkeypatch.setattr(sys, "argv", ["coverage.py", "check", "Etched raised $700M at $21B"])
    with pytest.raises(SystemExit) as exc:
        coverage.main()
    assert exc.value.code == 1


# --- add / list ------------------------------------------------------------

def test_add_creates_ledger_and_defaults_to_today(ledger):
    args = argparse.Namespace(slug="etched", headline="Etched raised $700M", entities=["Etched"],
                              angle="inference hardware", format="carousel", permalink="",
                              date=None)
    coverage.cmd_add(args)
    saved = json.loads(ledger.read_text())["entries"]
    assert saved == [{"date": coverage.today(), "slug": "etched", "headline": "Etched raised $700M",
                      "entities": ["Etched"], "angle": "inference hardware",
                      "format": "carousel", "permalink": ""}]


def test_add_appends_and_is_then_found_by_check(ledger):
    seed(ledger, entry(days_ago(30), "Old story", ["Oldco"]))
    coverage.cmd_add(argparse.Namespace(slug="x", headline="Chipco signs a $2B foundry deal",
                                        entities=["Chipco"], angle="", format="text",
                                        permalink="", date=days_ago(1)))
    assert len(json.loads(ledger.read_text())["entries"]) == 2
    assert check("Chipco foundry deal worth $2B") == 1


def test_list_shows_recent_newest_first(ledger, capsys):
    seed(ledger,
         entry(days_ago(3), "Middle story", []),
         entry(days_ago(20), "Ancient story", []),
         entry(days_ago(1), "Newest story", []))
    coverage.cmd_list(argparse.Namespace(days=7))
    out = capsys.readouterr().out
    assert "Ancient story" not in out
    assert out.index("Newest story") < out.index("Middle story")
