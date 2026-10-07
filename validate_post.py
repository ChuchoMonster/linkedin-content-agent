#!/usr/bin/env python3
"""Hard gates a post must clear before it can be scheduled to publish.

These are the rules from docs/01-voice-john.md and the hashtag section of
CLAUDE.md, enforced in code. A rule a script enforces does not erode; a rule in
a prompt does. Errors block scheduling. Warnings print and do not block.

Usage:
    python3 validate_post.py posts/2026-08-24-example.md
"""
import pathlib, re, sys

# Tags that mean the same thing. Two from one family is a wasted slot -- the
# 2026-08-15 post spent three of five saying "AI".
FAMILIES = [
    {"ai", "artificialintelligence", "aitech", "a.i."},
    {"generativeai", "genai"},
    {"llm", "llms", "largelanguagemodels"},
    {"aiagents", "agents", "agenticai", "aiagent"},
    {"automation", "aiautomation", "workflowautomation"},
    {"claude", "claudecode", "anthropic"},
    {"machinelearning", "ml", "deeplearning"},
    {"startup", "startups", "founders", "founder"},
]
BANNED = ["leverage", "unlock", "delve", "landscape", "game-changing", "game changing"]
NUDGES = ["which is its own tell", "here's the context that makes it",
          "the part i keep coming back to", "here's the part i keep",
          "that's not a round", "this isn't a deck", "what this means is",
          "the takeaway here"]


def check(path):
    raw = pathlib.Path(path).read_text().rstrip("\n")
    lines = raw.split("\n")
    errors, warnings = [], []

    # --- hashtags -------------------------------------------------------
    tag_line = lines[-1].strip()
    tags = re.findall(r"#\w+", tag_line)
    if not tags:
        errors.append("No hashtag line. Every post ends with exactly five hashtags.")
    elif len(tags) != 5:
        errors.append(f"{len(tags)} hashtags, must be exactly 5: {' '.join(tags)}")
    if tags and len(lines) >= 2 and lines[-2].strip() != "":
        errors.append("Hashtag line needs a blank line above it.")

    norm = [t[1:].lower() for t in tags]
    for fam in FAMILIES:
        dupes = [t for t, n in zip(tags, norm) if n in fam]
        if len(dupes) > 1:
            errors.append(f"Two hashtags mean the same thing: {' '.join(dupes)}")
    if len(set(norm)) != len(norm):
        errors.append("Duplicate hashtag.")

    body = "\n".join(lines[:-1]).strip() if tags else raw

    # --- typography -----------------------------------------------------
    for ch, name in (("—", "em dash"), ("–", "en dash")):
        if ch in body:
            errors.append(f"Contains an {name}. Use '--' or a period.")

    low = body.lower()
    for w in BANNED:
        if re.search(rf"\b{re.escape(w)}\b", low):
            errors.append(f"Banned word used: '{w}'")

    # --- shape ----------------------------------------------------------
    # File 04 says 100-180 words and an opener under 12. John's own published
    # rewrites break both -- he compressed Etched to 85 words, and his Gemini
    # opener runs 14. Hard-fail at the edges of what he has actually shipped;
    # warn inside the gap between the spec and his behaviour.
    words = len(body.split())
    if not 60 <= words <= 180:
        errors.append(f"{words} words. Outside 60-180.")
    elif words < 95:
        warnings.append(f"{words} words, under the 100 target in file 04. "
                        "His own rewrites run this short, so this may be fine.")

    first = body.split("\n")[0].strip()
    n_first = len(first.split())
    if n_first > 15:
        errors.append(f"Opening line is {n_first} words. Max 15.")
    elif n_first > 12:
        warnings.append(f"Opening line is {n_first} words, over the 12 in file 04. "
                        "His published Gemini opener is 14, so this may be fine.")
    if first.endswith("?"):
        errors.append("Opening line is a question. Questions belong at the end.")

    if not re.search(r"\d", body):
        errors.append("No number, price or duration anywhere in the post.")

    paras = [p for p in body.split("\n\n") if p.strip()]
    for i, p in enumerate(paras, 1):
        if len(p.split()) > 60:
            warnings.append(f"Paragraph {i} is {len(p.split())} words. He writes 1-2 sentences.")

    # --- the machine's habits -------------------------------------------
    # No closing question. John, 2026-08-23: "don't end with a question trying to
    # prompt people to comment. That's really cheesy." This overrides the
    # "genuine questions earn their place" carve-out in docs/01.
    body_lines = [l for l in body.split("\n") if l.strip()]
    if body_lines and body_lines[-1].strip().endswith("?"):
        errors.append("Post ends on a question. End on a verdict or a joke -- "
                      "no closing question, genuine or rhetorical.")

    for n in NUDGES:
        if n in low:
            warnings.append(f"Possible interpretive nudge: '{n}'")
    if re.search(r"anybody else (think|reading|seeing)\b", low):
        warnings.append("Closing question may be rhetorical -- 'Anybody else think [thesis]?' "
                        "is the take in disguise. Cut it and state the take.")

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    failed = False
    for path in sys.argv[1:]:
        errors, warnings = check(path)
        print(f"== {path}")
        for w in warnings:
            print(f"   WARN   {w}")
        for e in errors:
            print(f"   ERROR  {e}")
        if errors:
            failed = True
        elif not warnings:
            print("   OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
