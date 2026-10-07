#!/usr/bin/env python3
"""Read back the real status of Buffer posts. Never trust a status we did not re-read.

Usage:
    python3 buffer_status.py <post_id> [<post_id> ...]
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from buffer_draft import load_env, graphql

POST = """
query($input: PostInput!) {
  post(input: $input) {
    id status text dueAt createdAt channelId
    assets { __typename }
  }
}
"""

def fetch(env, pid):
    r = graphql(env, POST, {"input": {"id": pid}})
    if r.get("errors"):
        return {"id": pid, "error": json.dumps(r["errors"])[:300]}
    return (r.get("data") or {}).get("post") or {"id": pid, "error": "not found"}

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    env = load_env()
    for pid in sys.argv[1:]:
        p = fetch(env, pid)
        if p.get("error"):
            print(f"{pid}  ERROR  {p['error']}")
            continue
        first = (p.get("text") or "").strip().splitlines()[0][:58]
        assets = len(p.get("assets") or [])
        flag = "" if p["status"] == "draft" else "   <-- NOT A DRAFT"
        print(f"{p['id']}  {p['status']:<10} assets={assets}  due={p.get('dueAt')}{flag}")
        print(f"    {first}")

if __name__ == "__main__":
    main()
