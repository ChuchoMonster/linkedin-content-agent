#!/usr/bin/env python3
"""Create a Buffer draft post. Drafts only -- this never schedules or publishes.

Usage:
    python3 buffer_draft.py docs/gemini-1b-post.md
    python3 buffer_draft.py docs/gemini-1b-post.md --dry-run
    python3 buffer_draft.py post.md --document carousel-a.pdf
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).parent


def load_env(path=ROOT / ".env"):
    """Minimal .env reader. Real environment variables win over the file."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    env.update({k: v for k, v in os.environ.items() if k in env or k.startswith(("BUFFER_", "ASSET_"))})
    return env


def graphql(env, query, variables):
    request = urllib.request.Request(
        env.get("BUFFER_API_URL", "https://api.buffer.com"),
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {env['BUFFER_ACCESS_TOKEN']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return {"errors": [{"message": f"HTTP {exc.code}", "body": exc.read().decode()}]}


CREATE_POST = """
mutation CreateDraft($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post { id text status createdAt channelId }
    }
    ... on MutationError { message }
  }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="file containing the post text (.md or .txt)")
    parser.add_argument("--channel", help="Buffer channel id (defaults to BUFFER_LINKEDIN_CHANNEL_ID)")
    parser.add_argument("--document", help="public https URL of a PDF (carousels)")
    parser.add_argument("--document-title", help="required by LinkedIn whenever --document is used")
    parser.add_argument("--thumbnail", help="public https URL of the cover image for the PDF")
    parser.add_argument("--image", help="URL of an image to attach")
    parser.add_argument("--due-at", help="ISO8601 UTC time, e.g. 2026-08-18T12:00:00Z. Sets the "
                                         "intended slot. The post stays a draft until John "
                                         "promotes it -- this does not schedule it.")
    parser.add_argument("--dry-run", action="store_true", help="print the request without sending")
    args = parser.parse_args()

    env = load_env()
    if not env.get("BUFFER_ACCESS_TOKEN"):
        sys.exit("No BUFFER_ACCESS_TOKEN found in .env or the environment.")

    channel = args.channel or env.get("BUFFER_LINKEDIN_CHANNEL_ID")
    if not channel:
        sys.exit("No channel id. Pass --channel or set BUFFER_LINKEDIN_CHANNEL_ID.")

    text = pathlib.Path(args.source).read_text().strip()
    if not text:
        sys.exit(f"{args.source} is empty.")

    assets = []
    if args.document:
        # All three fields are required. LinkedIn silently refuses to schedule a
        # document post with no title, so fail here rather than in the queue.
        if not args.document_title or not args.thumbnail:
            sys.exit("--document needs both --document-title and --thumbnail.")
        for url in (args.document, args.thumbnail):
            if not url.startswith("https://"):
                sys.exit(f"Buffer fetches media at publish time, so {url} must be a public https URL, "
                         "not a local path. Host the file first.")
        assets.append({"document": {
            "url": args.document,
            "title": args.document_title,
            "thumbnailUrl": args.thumbnail,
        }})
    if args.image:
        assets.append({"image": {"url": args.image}})

    post_input = {
        "channelId": channel,
        "text": text,
        "assets": assets,
        "saveToDraft": True,  # the flag that keeps this out of the live queue
    }
    if args.due_at:
        post_input["dueAt"] = args.due_at
        post_input["schedulingType"] = "automatic"
        post_input["mode"] = "customScheduled"
    else:
        post_input["schedulingType"] = "automatic"
        post_input["mode"] = "addToQueue"

    variables = {"input": post_input}

    if args.dry_run:
        print(json.dumps(variables, indent=2))
        return

    result = graphql(env, CREATE_POST, variables)

    if result.get("errors"):
        print("FAILED. Request sent (token omitted):")
        print(json.dumps(variables, indent=2))
        print("\nResponse:")
        print(json.dumps(result, indent=2))
        sys.exit(1)

    payload = result["data"]["createPost"]
    if "message" in payload:
        print(f"Buffer rejected the post: {payload['message']}")
        sys.exit(1)

    post = payload["post"]
    print(f"Draft created.\n  id:      {post['id']}\n  status:  {post['status']}\n  channel: {post['channelId']}")
    if post["status"] != "draft":
        print(f"\nWARNING: status is '{post['status']}', not 'draft'. Check Buffer now.")
        sys.exit(1)


if __name__ == "__main__":
    main()
