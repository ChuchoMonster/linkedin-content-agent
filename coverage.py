#!/usr/bin/env python3
"""Ledger of what has already been posted, so the daily run never repeats a story.

A story is identified by its subject entities plus a short slug. The run checks
new candidates against the last N days before drafting anything. A repeat is
allowed only when the angle is genuinely different, and the run has to say so.

Usage:
    python3 coverage.py list [--days 7]
    python3 coverage.py check "Nvidia OpenAI Ohio data center financing"
    python3 coverage.py add --slug nvidia-ohio --entities Nvidia OpenAI \
        --headline "Nvidia backs $105B for OpenAI Ohio data center" \
        --angle "vendor financing / order book = loan book"
"""
import argparse, datetime, json, pathlib, re, sys, zoneinfo

ROOT = pathlib.Path(__file__).parent
LEDGER = ROOT / "coverage.json"
ET = zoneinfo.ZoneInfo("America/New_York")

STOP = {"the","a","an","of","for","to","in","on","and","its","it","is","at","as",
        "with","from","by","that","this","just","new","after","over","into","up"}


def today():
    return datetime.datetime.now(ET).date().isoformat()


def load():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {"entries": []}


def save(d):
    LEDGER.write_text(json.dumps(d, indent=2))


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9$.]+", text.lower()) if w not in STOP and len(w) > 2}


def overlap(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    # Floor the denominator: a one-token set would otherwise score 100% off a
    # single shared word like "openai", flagging every story about a big company.
    return len(ta & tb) / max(min(len(ta), len(tb)), 4)


def cmd_check(args):
    d = load()
    cutoff = (datetime.datetime.now(ET).date() - datetime.timedelta(days=args.days)).isoformat()
    hits = []
    for e in d["entries"]:
        if e["date"] < cutoff:
            continue
        score = max(overlap(args.text, e["headline"]),
                    overlap(args.text, " ".join(e.get("entities", []))))
        if score >= 0.5:
            hits.append((score, e))
    if not hits:
        print(f"CLEAR -- nothing similar in the last {args.days} days.")
        return 0
    print(f"OVERLAP -- {len(hits)} prior post(s). Only proceed on a genuinely new angle:")
    for score, e in sorted(hits, reverse=True, key=lambda x: x[0]):
        print(f"  {score:.0%}  {e['date']}  {e['headline']}")
        print(f"        angle already used: {e.get('angle','-')}")
    return 1


def cmd_add(args):
    d = load()
    d["entries"].append({
        "date": args.date or today(),
        "slug": args.slug,
        "headline": args.headline,
        "entities": args.entities,
        "angle": args.angle,
        "format": args.format,
        "permalink": args.permalink,
    })
    save(d)
    print(f"Logged {args.slug} ({d['entries'][-1]['date']}). {len(d['entries'])} entries total.")


def cmd_list(args):
    d = load()
    cutoff = (datetime.datetime.now(ET).date() - datetime.timedelta(days=args.days)).isoformat()
    rows = [e for e in d["entries"] if e["date"] >= cutoff]
    if not rows:
        print(f"Nothing in the last {args.days} days.")
        return
    for e in sorted(rows, key=lambda x: x["date"], reverse=True):
        print(f"{e['date']}  {e.get('format','text'):<8} {e['headline'][:64]}")
        print(f"            angle: {e.get('angle','-')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check"); c.add_argument("text"); c.add_argument("--days", type=int, default=7)
    c.set_defaults(fn=cmd_check)

    a = sub.add_parser("add")
    a.add_argument("--slug", required=True); a.add_argument("--headline", required=True)
    a.add_argument("--entities", nargs="*", default=[]); a.add_argument("--angle", default="")
    a.add_argument("--format", default="text"); a.add_argument("--permalink", default="")
    a.add_argument("--date", default=None)
    a.set_defaults(fn=cmd_add)

    l = sub.add_parser("list"); l.add_argument("--days", type=int, default=7)
    l.set_defaults(fn=cmd_list)

    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
