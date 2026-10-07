# The daily run

Fires 7:00 AM Eastern, Monday to Friday. Produces two posts that publish to
LinkedIn the same day at **8:30 AM ET** and **2:30 PM ET**.

**Monday to Thursday, the 2:30 PM slot is an op-ed.** That makes four op-eds and
six news posts a week. Friday is two news posts. John, 2026-09-14. See
"Op-ed days" below.

Those are publish times, not draft times. The posts are created as live
scheduled posts, and the window between creation and `dueAt` is John's veto.
Silence ships them.

## The chain

**1. Pull the stories.**
Search for today's AI news. Cast wider than five -- ten to fifteen candidates,
so there is something left after the dedupe cuts.

**2. Dedupe before drafting anything.**
```
python3 coverage.py check "<headline or one-line description>"
```
Exit 0 = clear. Exit 1 = we have covered it in the last 7 days, and the tool
prints the angle already used. A repeat is allowed **only** on a genuinely
different angle, and the run must say which angle in the notification. Same
story, same angle = drop it and take the next candidate.

**3. Pick the two best** (just one on op-ed days).
Judgment, not a formula. What earns a slot:
- It is about money, scale, or a decision someone has to make. Not a demo.
- The numbers are specific and attributable.
- John's audience -- B2B operators, PE, SaaS, marketing leaders -- would care.
Prefer two stories that are *different from each other*. Two funding rounds in
one day is one story told twice.

**4. Choose format per story.**
The rule from CLAUDE.md: best-sourced stories go to carousels, because a frame
has no room for a "reportedly". A story resting on second-hand numbers, or one
a company disputes, goes to text where it can be hedged.

**5. Draft.**
Load `01-voice-john.md` and both files in `examples/` every time. The five things
he fixes are in CLAUDE.md. Highest-value checks, from his own rewrites:
- Join clauses with "and"/"but" instead of stacking declaratives.
- Delete every line that tells the reader what the previous fact means.
- Cut true facts that do not serve the one idea.
- **No closing question.** End on a verdict or a joke. Hard gate.
- Exactly five hashtags, one each for domain, subject, application, audience, angle.

**6. Validate. This blocks.**
```
python3 validate_post.py posts/<file>.md
```
Non-zero exit means do not schedule. Fix the draft, do not pass
`--skip-validation`. That flag exists for John, not for the run.

**7. Carousel, if the story earned one.**
```
python3 render_carousel.py carousels/<slug>.json     # enforces 4-or-6 frames, 18 words
python3 publish_asset.py <slug>                      # hosts + verifies HTTP 200
```
`publish_asset.py` refuses to return URLs it has not confirmed are live.

**8. Schedule both.**
```
python3 buffer_schedule.py posts/<morning>.md --at <YYYY-MM-DD>T08:30
python3 buffer_schedule.py posts/<afternoon>.md --at <YYYY-MM-DD>T14:30 \
    --document <https url> --document-title "<title>" --thumbnail <https url>
```
Times are Eastern; the script converts and handles DST. It refuses anything
under 15 minutes out, anything in the past, and any non-https asset.

Confirm `status: scheduled` on both. Never report a scheduled post without it.

**9. Log coverage.** One `coverage.py add` per post, with the angle used and the
post id.

**10. Notify John.** One message with, for each post: publish time, the full
text, the carousel link if any, and the exact kill command. He must be able to
veto by copying one line. Label an op-ed **OP-ED** so he can find it fast.

## Op-ed days -- Monday to Thursday, 2:30 PM slot

Run the chain above for **one** news story at 8:30 AM. Fill 2:30 PM with an op-ed.

**1. Take the queue first.**
`drafts/oped/queue/` holds op-eds John has already approved. Use the
lowest-numbered file. Before scheduling it:
- Re-check every relative date against the publish date. "Last Tuesday", "this
  fall" and "in August" go stale. Fix the wording, or leave the file in the queue
  and take the next one.
- Check whether a newer report has replaced any figure in it, like a monthly jobs
  number.
- Copy it to `posts/<YYYY-MM-DD>-oped-<slug>.md`, validate, schedule, and only
  then delete it from the queue.

**2. If the queue is empty, write one.**
- **Only argue positions that are in `docs/06-oped-themes.md`.** Never invent an
  opinion for John. New themes come from him.
- Peg it to something current where you can. A news hook makes a standing
  argument timely. One theme point can carry a post, or two or three can combine.
- Read the fact-check notes under the theme and follow them. They exist
  because the first drafts got facts wrong -- attributing one company's
  political funding to a competitor, and an IPO timeline to the wrong lab.
- Run `python3 coverage.py list --days 21`. Don't reuse a theme and point
  combination that ran in the last three weeks.
- The voice rules match the news posts, with one exception. An op-ed is an
  argument, so a line that says what a fact means is allowed. The approved queue
  files show how much of that is right.

**3. Named people.**
Saying that someone's timing or behavior looks suspicious is opinion, and that's
fine. Stating as fact that a named person did something dishonest, staged or
coordinated is never allowed. If they have denied it, the post says so.

**4. Format.** Text by default. Op-eds hedge, and a carousel frame has no room
for that.

**5. Same gates.** `validate_post.py` must pass. Log it with
`coverage.py add --slug oped-<slug>` and an angle that names the theme and
points used, e.g. `theme 1: A+B+D`.

**6. Fallback.** If the queue is empty and there is no honest op-ed to write
today, run a second news story instead and say so in the notification. Don't
pad an argument.

Op-eds ship on silence, like everything else in this run.

## Killing a post

```
python3 buffer_schedule.py --cancel <post_id>
```
Works any time before `dueAt`. After it publishes, the only remedy is deleting
it on LinkedIn, and by then it has been seen.

## Hard rules

- Never invent a number, client, outcome, or date.
- Never name a client not already named in the source.
- Story cards flagged PERSONAL are never used without John clearing them.
- If the day's news is thin, ship **one** post, or none. Two mediocre posts is
  worse than one good one. Say so in the notification.
- If any step fails, schedule nothing and tell John what broke.
