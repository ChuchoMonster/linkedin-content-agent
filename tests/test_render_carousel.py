"""Carousel spec validation and HTML rendering. Chrome is never launched."""
import json
import sys

import pytest

import render_carousel
from conftest import ROOT


def frame(kind="head", **kw):
    base = {"type": kind, "eyebrow": "Eyebrow", "text": "Short line of text."}
    base.update(kw)
    return base


def spec(frames):
    return {"slug": "test-deck", "frames": frames}


@pytest.mark.parametrize("n", [3, 4, 5, 6, 7])
def test_only_four_or_six_frames_are_accepted(n):
    if n in (4, 6):
        html = render_carousel.build_html(spec([frame()] * n))
        assert html.count('<div class="frame ') == n
        assert f"{n:02d} / {n:02d}" in html
    else:
        with pytest.raises(SystemExit, match=f"This spec has {n}"):
            render_carousel.build_html(spec([frame()] * n))


def test_word_limit_counts_text_body_and_stat_together():
    ok = frame("stat", stat="$21B", text=" ".join(["w"] * 17))           # 18 words
    too_many = frame("head", text=" ".join(["w"] * 10), body=" ".join(["w"] * 9))  # 19
    render_carousel.build_html(spec([ok] * 4))
    with pytest.raises(SystemExit, match="Frame 2 has 19 words"):
        render_carousel.build_html(spec([ok, too_many, ok, ok]))


def test_unknown_background_and_frame_type_are_rejected():
    with pytest.raises(SystemExit, match="Unknown bg: neon"):
        render_carousel.render_frame(frame(bg="neon"), 1, 4)
    with pytest.raises(SystemExit, match="Unknown frame type: chart"):
        render_carousel.render_frame(frame("chart"), 1, 4)


def test_stat_frame_markup():
    html = render_carousel.render_frame(frame("stat", bg="band", stat="$700M",
                                              text="Raised this week."), 3, 6)
    assert '<div class="frame band">' in html
    assert '<div class="stat">$700M</div>' in html
    assert '<div class="label">Raised this week.</div>' in html
    assert '<div class="counter">03 / 06</div>' in html


def test_head_frame_body_is_optional():
    with_body = render_carousel.render_frame(frame(body="Supporting line."), 1, 4)
    without = render_carousel.render_frame(frame(), 1, 4)
    assert '<div class="body">Supporting line.</div>' in with_body
    assert 'class="body"' not in without
    assert '<div class="frame paper">' in without   # default background


def test_every_shipped_carousel_spec_still_builds():
    specs = sorted((ROOT / "carousels").glob("*.json"))
    assert specs
    for path in specs:
        html = render_carousel.build_html(json.loads(path.read_text()))
        assert html.startswith("<!doctype html>"), path.name


def test_main_prints_pdf_and_cover_via_chrome(tmp_path, monkeypatch, capsys):
    deck = tmp_path / "deck.json"
    deck.write_text(json.dumps(spec([frame()] * 4)))
    commands = []
    monkeypatch.setattr(render_carousel, "BUILD", tmp_path / "build")
    monkeypatch.setattr(render_carousel, "CHROME", "/fake/chrome")
    monkeypatch.setattr(render_carousel.subprocess, "run",
                        lambda cmd, **kw: commands.append((cmd, kw)))
    monkeypatch.setattr(sys, "argv", ["render_carousel.py", str(deck)])

    render_carousel.main()

    html_file = tmp_path / "build" / "test-deck.html"
    assert html_file.exists()
    (pdf_cmd, pdf_kw), (png_cmd, _) = commands
    assert pdf_cmd[0] == "/fake/chrome" and "--headless" in pdf_cmd
    assert f"--print-to-pdf={tmp_path / 'build' / 'test-deck.pdf'}" in pdf_cmd
    assert f"--screenshot={tmp_path / 'build' / 'test-deck-cover.png'}" in png_cmd
    assert "--window-size=1200,1500" in png_cmd
    assert pdf_kw["check"] is True
    assert "(4 frames)" in capsys.readouterr().out
