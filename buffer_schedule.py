#!/usr/bin/env python3
"""Schedule a post to PUBLISH on LinkedIn at a given Eastern time.

Unlike buffer_draft.py, this creates a live scheduled post -- it will go out on
its own. That is the point: the gate is the window between now and dueAt, during
which --cancel removes it. Silence ships it.

    python3 buffer_schedule.py posts/x.md --at 2026-08-24T08:30 --dry-run
    python3 buffer_schedule.py posts/x.md --at 2026-08-24T08:30 \
        --document https://.../x.pdf --document-title "..." \
        --thumbnail https://.../x-cover.png
    python3 buffer_schedule.py --cancel <post_id>
"""
import argparse, datetime, json, pathlib, sys, zoneinfo

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))
from buffer_draft import load_env, graphql, CREATE_POST
from validate_post import check as validate

ET = zoneinfo.ZoneInfo("America/New_York")
LEAD_MINUTES = 15

DELETE_POST = """
mutation Kill($input: DeletePostInput!) {
  deletePost(input: $input) {
    ... on PostActionSuccess { post { id status } }
    ... on MutationError { message }
  }
}
"""


def to_utc(stamp):
    """'2026-08-24T08:30' in Eastern -> aware UTC datetime. Handles DST."""
    naive = datetime.datetime.fromisoformat(stamp)
    if naive.tzinfo is not None:
        return naive.astimezone(datetime.timezone.utc)
    return naive.replace(tzinfo=ET).astimezone(datetime.timezone.utc)


def cancel(env, pid):
    r = graphql(env, DELETE_POST, {"input": {"id": pid}})
    if r.get("errors"):
        sys.exit(json.dumps(r["errors"], indent=2))
    payload = r["data"]["deletePost"]
    if "message" in payload:
        sys.exit(f"Buffer refused: {payload['message']}")
    print(f"Cancelled {pid}. It will not publish.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", help="file containing the post text")
    ap.add_argument("--at", help="Eastern time, e.g. 2026-08-24T08:30")
    ap.add_argument("--channel")
    ap.add_argument("--document"); ap.add_argument("--document-title"); ap.add_argument("--thumbnail")
    ap.add_argument("--cancel", metavar="POST_ID", help="cancel a scheduled post before it fires")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-validation", action="store_true",
                    help="publish despite failing gates. Requires a reason on the record.")
    ap.add_argument("--now-if-past", action="store_true",
                    help="if --at has already passed, publish immediately instead of failing. "
                         "There is NO cancel window on a post sent this way.")
    args = ap.parse_args()

    env = load_env()
    if not env.get("BUFFER_ACCESS_TOKEN"):
        sys.exit("No BUFFER_ACCESS_TOKEN.")

    if args.cancel:
        return cancel(env, args.cancel)
    if not args.source or not args.at:
        sys.exit("Need a source file and --at (or --cancel).")

    errors, warnings = validate(args.source)
    for w in warnings:
        print(f"WARN   {w}")
    if errors:
        for e in errors:
            print(f"ERROR  {e}")
        if not args.skip_validation:
            sys.exit("Refusing to schedule a post that fails the gates.")
        print("Proceeding anyway because --skip-validation was passed.")

    due = to_utc(args.at)
    now = datetime.datetime.now(datetime.timezone.utc)
    too_late = (due - now).total_seconds() < LEAD_MINUTES * 60

    # John, 2026-08-23: if the laptop opens after the morning slot, send it then
    # rather than dropping the post. shareNow has no dueAt, so there is no window
    # in which --cancel can reach it. That is the trade he asked for.
    publish_now = too_late and args.now_if_past
    if too_late and not publish_now:
        if due <= now:
            sys.exit(f"{args.at} ET is in the past. Pass --now-if-past to send it anyway.")
        sys.exit(f"{args.at} ET is less than {LEAD_MINUTES} minutes out. "
                 "That leaves no window to cancel. Pass --now-if-past to send it anyway.")

    channel = args.channel or env.get("BUFFER_LINKEDIN_CHANNEL_ID")
    text = pathlib.Path(args.source).read_text().strip()

    assets = []
    if args.document:
        if not (args.document_title and args.thumbnail):
            sys.exit("--document needs --document-title and --thumbnail.")
        for u in (args.document, args.thumbnail):
            if not u.startswith("https://"):
                sys.exit(f"{u} must be a public https URL. Run publish_asset.py first.")
        assets.append({"document": {"url": args.document, "title": args.document_title,
                                    "thumbnailUrl": args.thumbnail}})

    post_input = {
        "channelId": channel,
        "text": text,
        "assets": assets,
        "saveToDraft": False,          # deliberate: this publishes
        "schedulingType": "automatic",  # 'notification' would only remind John
    }
    if publish_now:
        post_input["mode"] = "shareNow"
    else:
        post_input["mode"] = "customScheduled"
        post_input["dueAt"] = due.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    local = due.astimezone(ET).strftime("%a %b %d, %-I:%M %p %Z")
    if args.dry_run:
        print(f"DRY RUN -- would PUBLISH IMMEDIATELY (slot {local} already passed)"
              if publish_now else f"DRY RUN -- would publish {local}")
        print(json.dumps({"input": post_input}, indent=2))
        return

    result = graphql(env, CREATE_POST, {"input": post_input})
    if result.get("errors"):
        print(json.dumps(result, indent=2)); sys.exit(1)
    payload = result["data"]["createPost"]
    if "message" in payload:
        sys.exit(f"Buffer rejected it: {payload['message']}")

    post = payload["post"]
    if publish_now:
        print(f"PUBLISHED NOW -- the {local} slot had already passed.")
        print(f"  id:     {post['id']}")
        print(f"  status: {post['status']}")
        if post["status"] not in ("sending", "sent"):
            print(f"\nWARNING: expected 'sending' or 'sent', got '{post['status']}'.")
            sys.exit(1)
        print("\n  This one is already out. There was no cancel window.")
        return

    print(f"SCHEDULED TO PUBLISH  {local}")
    print(f"  id:     {post['id']}")
    print(f"  status: {post['status']}")
    if post["status"] != "scheduled":
        print(f"\nWARNING: expected 'scheduled', got '{post['status']}'. Check Buffer now.")
        sys.exit(1)
    print(f"\n  To kill it:  python3 buffer_schedule.py --cancel {post['id']}")


if __name__ == "__main__":
    main()
