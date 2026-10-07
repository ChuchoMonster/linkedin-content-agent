#!/bin/zsh
# Daily run for the LinkedIn content agent. Fired by launchd (or cron) at
# 7:00am Eastern, Mon-Fri.
# launchd schedules in local time, so this stays at 7am through the DST change.
#
# If the Mac was asleep at 7am, launchd fires this on wake. The run passes
# --now-if-past on the morning slot only, so a post whose 8:30 slot has already
# gone by is published immediately rather than dropped. Author's call, 2026-08-23.

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:/usr/bin:/bin:/usr/sbin:/sbin"
# Run from the repo root, wherever it is checked out. Override with AGENT_HOME.
cd "${AGENT_HOME:-$(dirname "$0")}" || exit 1

# Model choices are overridable without editing this file.
MODEL="${CLAUDE_MODEL:-claude-opus-5}"
FALLBACK_MODEL="${CLAUDE_FALLBACK_MODEL:-claude-sonnet-5}"

STAMP=$(date +%Y-%m-%d)
LOG="logs/daily-$STAMP.log"
mkdir -p logs

PROMPT="Run the daily run. The full procedure is in docs/05-daily-run.md -- read it first, and read CLAUDE.md, docs/01-voice-john.md and both files in docs/examples/ before drafting anything.

Today's two posts publish at 8:30am and 2:30pm Eastern.

Monday to Thursday the 2:30pm post is an op-ed, not news. Follow the Op-ed days section of docs/05-daily-run.md and read docs/06-oped-themes.md first. Take the next approved op-ed from drafts/oped/queue before writing a new one. Friday is two news posts.

Schedule the morning post with:
  python3 buffer_schedule.py posts/<file>.md --at <today>T08:30 --now-if-past
Schedule the afternoon post with:
  python3 buffer_schedule.py posts/<file>.md --at <today>T14:30

--now-if-past belongs on the morning slot only. If the machine woke late and 8:30
has passed, that post goes out immediately with no cancel window. The 2:30 post
must never use it -- if 2:30 has also passed, skip that post and say so.

Do not pass --skip-validation. If a draft fails validate_post.py, fix the draft.
If you cannot get two good stories past the dedupe check, ship one, or none.

Finish by writing a summary to stdout: for each post, the publish time, the full
text, the carousel link if any, and the exact --cancel command."

{
  echo "=== daily run: $(date '+%Y-%m-%d %H:%M:%S %Z') ==="

  claude -p "$PROMPT" \
    --permission-mode bypassPermissions \
    --model "$MODEL" \
    --fallback-model "$FALLBACK_MODEL"
  STATUS=$?

  echo "=== exit=$STATUS finished $(date '+%H:%M:%S %Z') ==="
} >> "$LOG" 2>&1

# Surface the result on screen (macOS) so the author sees it when the laptop opens.
/usr/bin/osascript -e "display notification \"Check logs/daily-$STAMP.log\" with title \"Content agent run finished\"" 2>/dev/null || true
