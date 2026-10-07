#!/usr/bin/env python3
"""Put a rendered carousel on a public https URL so Buffer can fetch it.

Buffer downloads carousel media at publish time, not at upload time, so the PDF
and its cover have to stay reachable until the post actually goes out. Filenames
are content-hashed: re-rendering a carousel never overwrites the file a pending
post is pointing at.

Usage:
    python3 publish_asset.py nvidia-ohio --dry-run
    python3 publish_asset.py nvidia-ohio
"""

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
from buffer_draft import load_env

BUILD = ROOT / "build"
MANIFEST = BUILD / "hosted-assets.json"
ENV = load_env()


def config():
    """Hosting settings come from .env or the environment -- see .env.example.

    ASSET_SITE_DIR   local checkout of the static site that hosts the files
    ASSET_PUBLISH_DIR  the site's publish directory, relative to ASSET_SITE_DIR
    ASSET_BASE_URL   public https URL that serves <publish dir>/assets/carousels
    """
    site = ENV.get("ASSET_SITE_DIR")
    base = ENV.get("ASSET_BASE_URL")
    if not site or not base:
        sys.exit("Set ASSET_SITE_DIR and ASSET_BASE_URL in .env (see .env.example).")
    site = pathlib.Path(site).expanduser()
    publish = ENV.get("ASSET_PUBLISH_DIR", "site")
    return site, publish, site / publish / "assets" / "carousels", base.rstrip("/")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slug", help="carousel slug, e.g. nvidia-ohio")
    ap.add_argument("--dry-run", action="store_true",
                    help="stage the files and print the URLs without deploying")
    args = ap.parse_args()

    pdf = BUILD / f"{args.slug}.pdf"
    png = BUILD / f"{args.slug}-cover.png"
    for f in (pdf, png):
        if not f.exists():
            sys.exit(f"Missing {f}. Run render_carousel.py first.")

    # 100MB is Buffer's document ceiling. Fail here, not in the queue.
    size_mb = pdf.stat().st_size / 1_048_576
    if size_mb > 100:
        sys.exit(f"{pdf.name} is {size_mb:.1f}MB. LinkedIn documents must be under 100MB.")

    SITE, PUBLISH_DIR, ASSET_DIR, BASE_URL = config()

    stamp = digest(pdf)
    pdf_name = f"{args.slug}-{stamp}.pdf"
    png_name = f"{args.slug}-{stamp}-cover.png"

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for src, name in ((pdf, pdf_name), (png, png_name)):
        dest = ASSET_DIR / name
        if dest.exists() and digest(dest) == digest(src):
            continue  # identical content already hosted, leave it alone
        shutil.copy2(src, dest)

    pdf_url = f"{BASE_URL}/{pdf_name}"
    png_url = f"{BASE_URL}/{png_name}"

    if args.dry_run:
        print("DRY RUN -- files staged, nothing deployed.")
        print(f"  staged: {ASSET_DIR / pdf_name}")
        print(f"  staged: {ASSET_DIR / png_name}")
        print(f"\n  --document       {pdf_url}")
        print(f"  --thumbnail      {png_url}")
        return

    result = subprocess.run(
        ["netlify", "deploy", "--prod", "--dir", PUBLISH_DIR],
        cwd=SITE, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit("Netlify deploy failed. Nothing is hosted -- do not create the post.")

    # Never report a URL we have not confirmed is live.
    for url in (pdf_url, png_url):
        check = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                                "-L", "--max-time", "30", url], capture_output=True, text=True)
        if check.stdout.strip() != "200":
            sys.exit(f"{url} returned {check.stdout.strip()}, not 200. Do not create the post.")

    manifest = load_manifest()
    manifest[pdf_name] = {"slug": args.slug, "pdf": pdf_url, "thumbnail": png_url}
    MANIFEST.write_text(json.dumps(manifest, indent=2))

    print("Hosted and verified live (HTTP 200 on both).")
    print(f"  --document       {pdf_url}")
    print(f"  --thumbnail      {png_url}")


if __name__ == "__main__":
    main()
