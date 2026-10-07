"""Hosting carousels: content-hashed names, and never trusting an unverified URL."""
import hashlib
import json
import sys
import types

import pytest

import publish_asset


@pytest.fixture
def site(tmp_path, monkeypatch):
    build = tmp_path / "build"
    build.mkdir()
    (build / "deck.pdf").write_bytes(b"%PDF fake deck")
    (build / "deck-cover.png").write_bytes(b"fake png")
    site_dir = tmp_path / "site-checkout"
    monkeypatch.setattr(publish_asset, "BUILD", build)
    monkeypatch.setattr(publish_asset, "MANIFEST", build / "hosted-assets.json")
    monkeypatch.setattr(publish_asset, "ENV", {"ASSET_SITE_DIR": str(site_dir),
                                               "ASSET_PUBLISH_DIR": "public",
                                               "ASSET_BASE_URL": "https://cdn.example.com/c/"})
    stamp = hashlib.sha256(b"%PDF fake deck").hexdigest()[:8]
    return types.SimpleNamespace(build=build, site=site_dir, stamp=stamp,
                                 assets=site_dir / "public" / "assets" / "carousels")


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["publish_asset.py", *argv])
    publish_asset.main()


def fake_subprocess(monkeypatch, netlify_rc=0, http_code="200"):
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "netlify":
            return types.SimpleNamespace(returncode=netlify_rc, stdout="", stderr="deploy error")
        return types.SimpleNamespace(returncode=0, stdout=http_code, stderr="")

    monkeypatch.setattr(publish_asset.subprocess, "run", fake_run)
    return calls


def test_missing_render_output_stops_early(site, monkeypatch):
    (site.build / "deck-cover.png").unlink()
    with pytest.raises(SystemExit, match="Run render_carousel.py first"):
        run(monkeypatch, "deck")


def test_dry_run_stages_content_hashed_files_without_deploying(site, monkeypatch, capsys):
    calls = fake_subprocess(monkeypatch)
    run(monkeypatch, "deck", "--dry-run")
    assert (site.assets / f"deck-{site.stamp}.pdf").read_bytes() == b"%PDF fake deck"
    assert (site.assets / f"deck-{site.stamp}-cover.png").exists()
    assert calls == []
    assert f"https://cdn.example.com/c/deck-{site.stamp}.pdf" in capsys.readouterr().out


def test_deploy_then_verify_both_urls_before_recording(site, monkeypatch):
    calls = fake_subprocess(monkeypatch)
    run(monkeypatch, "deck")
    assert calls[0] == ["netlify", "deploy", "--prod", "--dir", "public"]
    checked = [c[-1] for c in calls[1:]]
    assert checked == [f"https://cdn.example.com/c/deck-{site.stamp}.pdf",
                       f"https://cdn.example.com/c/deck-{site.stamp}-cover.png"]
    manifest = json.loads((site.build / "hosted-assets.json").read_text())
    assert manifest[f"deck-{site.stamp}.pdf"]["slug"] == "deck"


def test_url_that_is_not_200_blocks_the_post(site, monkeypatch):
    fake_subprocess(monkeypatch, http_code="404")
    with pytest.raises(SystemExit, match="returned 404, not 200"):
        run(monkeypatch, "deck")
    assert not (site.build / "hosted-assets.json").exists()


def test_failed_deploy_never_checks_urls(site, monkeypatch):
    calls = fake_subprocess(monkeypatch, netlify_rc=1)
    with pytest.raises(SystemExit, match="Netlify deploy failed"):
        run(monkeypatch, "deck")
    assert [c[0] for c in calls] == ["netlify"]
