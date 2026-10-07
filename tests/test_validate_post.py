"""Every gate in validate_post.check(), with a passing and a failing case."""
import pathlib
import sys

import pytest

import validate_post
from conftest import ROOT, VALID_BODY, VALID_TAGS, make_post


def errors_and_warnings(write_post, text):
    return validate_post.check(write_post(text))


def test_reference_post_is_clean(write_post):
    errors, warnings = errors_and_warnings(write_post, make_post())
    assert errors == []
    assert warnings == []


# --- hashtags ---------------------------------------------------------------

def test_missing_hashtag_line_is_an_error(write_post):
    errors, _ = errors_and_warnings(write_post, make_post(tags=None))
    assert any("No hashtag line" in e for e in errors)


@pytest.mark.parametrize("tags", ["#One #Two #Three #Four",
                                  "#One #Two #Three #Four #Five #Six"])
def test_hashtag_count_must_be_exactly_five(write_post, tags):
    errors, _ = errors_and_warnings(write_post, make_post(tags=tags))
    assert any("must be exactly 5" in e for e in errors)


def test_hashtag_line_needs_a_blank_line_above(write_post):
    text = f"{VALID_BODY}\n{VALID_TAGS}\n"
    errors, _ = errors_and_warnings(write_post, text)
    assert "Hashtag line needs a blank line above it." in errors


@pytest.mark.parametrize("pair", [("#AI", "#ArtificialIntelligence"),
                                  ("#genai", "#GenerativeAI")])
def test_two_tags_from_one_family_are_rejected(write_post, pair):
    tags = f"{pair[0]} {pair[1]} #Semiconductors #DeepTech #Inference"
    errors, _ = errors_and_warnings(write_post, make_post(tags=tags))
    assert any("Two hashtags mean the same thing" in e for e in errors)


def test_tags_from_different_families_are_allowed(write_post):
    tags = "#AI #GenAI #LLM #Automation #MachineLearning"
    errors, _ = errors_and_warnings(write_post, make_post(tags=tags))
    assert errors == []


def test_exact_duplicate_tag_is_rejected_case_insensitively(write_post):
    tags = "#Fintech #fintech #Semiconductors #DeepTech #Inference"
    errors, _ = errors_and_warnings(write_post, make_post(tags=tags))
    assert "Duplicate hashtag." in errors


# --- typography and vocabulary ----------------------------------------------

@pytest.mark.parametrize("dash, name", [("—", "em dash"), ("–", "en dash")])
def test_em_and_en_dashes_are_rejected(write_post, dash, name):
    body = VALID_BODY.replace("not a venture fund", f"not a venture fund{dash}a trader")
    errors, _ = errors_and_warnings(write_post, make_post(body=body))
    assert any(name in e for e in errors)


@pytest.mark.parametrize("word", ["leverage", "delve", "game-changing"])
def test_banned_words_are_rejected(write_post, word):
    body = VALID_BODY.replace("quietly moved", f"quietly moved to {word} and moved")
    errors, _ = errors_and_warnings(write_post, make_post(body=body))
    assert f"Banned word used: '{word}'" in errors


def test_banned_word_match_is_whole_word_only(write_post):
    # "leveraged" and "unlocked" are different words; the rule targets the cliches.
    body = VALID_BODY.replace("quietly moved", "leveraged buyers unlocked and moved")
    errors, _ = errors_and_warnings(write_post, make_post(body=body))
    assert errors == []


# --- shape ------------------------------------------------------------------

def _body_of(n_words):
    opener = "A chip startup doubled its value in 4 weeks."  # 9 words, has a number
    filler = " ".join(["word"] * (n_words - 9))
    return f"{opener}\n\n{filler}."


@pytest.mark.parametrize("n, blocked", [(59, True), (60, False), (94, False),
                                       (180, False), (181, True)])
def test_word_count_limits(write_post, n, blocked):
    errors, warnings = errors_and_warnings(write_post, make_post(body=_body_of(n)))
    assert any("Outside 60-180" in e for e in errors) == blocked
    # Inside the hard limits but under the 100-word target: a warning, not a block.
    assert any("under the 100 target" in w for w in warnings) == (60 <= n < 95)


@pytest.mark.parametrize("n_words, error, warning", [(16, True, False), (13, False, True),
                                                    (12, False, False)])
def test_opening_line_length(write_post, n_words, error, warning):
    opener = " ".join(f"w{i}" for i in range(n_words))
    body = VALID_BODY.replace(VALID_BODY.split("\n")[0], opener)
    errors, warnings = errors_and_warnings(write_post, make_post(body=body))
    assert any(f"Opening line is {n_words} words. Max 15." == e for e in errors) == error
    assert any(f"Opening line is {n_words} words, over the 12" in w for w in warnings) == warning


def test_opening_question_is_an_error(write_post):
    body = VALID_BODY.replace("in four weeks.", "in four weeks?", 1)
    errors, _ = errors_and_warnings(write_post, make_post(body=body))
    assert any("Opening line is a question" in e for e in errors)


def test_post_without_any_number_is_an_error(write_post):
    body = "".join(ch for ch in VALID_BODY if not ch.isdigit())
    errors, _ = errors_and_warnings(write_post, make_post(body=body))
    assert any("No number" in e for e in errors)


def test_long_paragraph_warns_but_does_not_block(write_post):
    long_post = make_post(body="Opener with 1 number.\n\n" + " ".join(["word"] * 61) + ".")
    errors, warnings = errors_and_warnings(write_post, long_post)
    assert errors == []
    assert any("Paragraph 2 is 61 words" in w for w in warnings)


# --- the machine's habits ---------------------------------------------------

def test_only_a_closing_question_is_an_error(write_post):
    closing = VALID_BODY + "\n\nWho is buying these chips next?"
    errors, _ = errors_and_warnings(write_post, make_post(body=closing))
    assert any("Post ends on a question" in e for e in errors)

    mid = VALID_BODY.replace("Trading firms care", "Why a trader? Trading firms care")
    errors, _ = errors_and_warnings(write_post, make_post(body=mid))
    assert errors == []


def test_interpretive_nudge_warns_but_does_not_block(write_post):
    body = VALID_BODY.replace("The money", "The takeaway here is simple. The money")
    errors, warnings = errors_and_warnings(write_post, make_post(body=body))
    assert errors == []
    assert "Possible interpretive nudge: 'the takeaway here'" in warnings


def test_rhetorical_anybody_else_question_is_flagged(write_post):
    body = VALID_BODY + "\n\nAnybody else think inference wins?"
    errors, warnings = errors_and_warnings(write_post, make_post(body=body))
    assert any("Closing question may be rhetorical" in w for w in warnings)
    assert any("Post ends on a question" in e for e in errors)


# --- the published sample, and the command line ------------------------------

def test_published_sample_matches_readme_claim():
    """README: the two earliest posts fail today's validator; the rest pass."""
    posts = sorted((ROOT / "posts").glob("*.md"))
    assert len(posts) >= 3
    results = {p.name: validate_post.check(p)[0] for p in posts}
    failing = sorted(name for name, errors in results.items() if errors)
    assert failing == [p.name for p in posts[:2]]


def test_cli_exit_code_reflects_failures(write_post, monkeypatch, capsys):
    good = write_post(make_post())
    bad = write_post(make_post(tags=None))

    monkeypatch.setattr(sys, "argv", ["validate_post.py", str(good)])
    with pytest.raises(SystemExit) as ok:
        validate_post.main()
    assert ok.value.code == 0
    assert "OK" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["validate_post.py", str(good), str(bad)])
    with pytest.raises(SystemExit) as fail:
        validate_post.main()
    assert fail.value.code == 1
