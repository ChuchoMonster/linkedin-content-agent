# LinkedIn content agent — John's content factory

> Public portfolio copy. This file is the agent's operating manual (Claude Code
> loads it automatically). Personal material has been replaced with fictional
> examples; see README.md for the overview.

Turns a source into LinkedIn drafts in John's voice. The machine does ~80%; John's
review is the last step and it is not optional.

## Load these before drafting anything

- [docs/01-voice-john.md](docs/01-voice-john.md) — voice, register, fact economy, 10 checks a draft must pass
- [docs/02-visual-design-system.md](docs/02-visual-design-system.md) — carousel palette, type, layout
- [docs/03-story-bank-john.csv](docs/03-story-bank-john.csv) — story cards (6 fictional examples in this public copy)
- [docs/04-channel-skill-john.md](docs/04-channel-skill-john.md) — the worker spec
- [docs/examples/](docs/examples/) — **read these every time.** Machine drafts next to
  John's rewrites, with the rule each edit produces. `gemini-before-after.md` and
  `etched-teens-before-after.md`.

If one is missing, stop and say which. Never guess at his voice or his stories.

## What John fixes, every time

Drawn from three rewrites across 2026-08-15 and 08-18. Details and diffs in
[docs/examples/](docs/examples/).

1. **Too pointed.** The machine stacks hard declaratives. He joins them and
   lightens them. "AI writing is very pointed... I write a little bit lighter,
   easier to read, less harsh, less direct." The opening line usually ends up with
   an exclamation point.
2. **Interpretive nudges after every fact.** The machine writes a line telling the
   reader what the fact means -- "That's not a round, that's a re-rating", "which
   is its own tell", "Here's the context that makes it interesting". He deletes
   all of them. State the fact, stack related facts together, and save the
   interpretation for the last line.
3. **Too many facts.** He cuts true, sourced facts that don't serve the one idea.
   Having a fact is not a reason to use it.
4. **A forced story.** The story bank is optional. A post with no story card is a
   finished post.
5. **A rhetorical closing question.** "Anybody else think [my thesis]?" is the take
   in disguise -- he cuts it and states the take, often very compressed ("Models =
   commodities. Inference is where the alpha comes from."). A question he
   genuinely wants answered survives untouched.

What he does **not** change: sourcing caveats ("reportedly", "grain of salt"),
admissions of uncertainty, naming what he doesn't do, and the hashtag sets.

## Hashtags

Every post ends with a hashtag line, blank line above it. **Exactly five, and no
standing set — they are chosen per post.**

LinkedIn dropped hashtag-following in early 2025. Tags no longer bring an
audience; they tell the classifier what the post is about so it can decide who to
show it to. That makes a hashtag a slot in a description, not a keyword to stuff.

**Each of the five covers a different facet. Never two that mean the same thing.**

1. **Domain** — the field. `#ArtificialIntelligence` *or* `#AI`, never both.
2. **Subject** — the specific thing the post is about. `#Gemini`, `#ClaudeCode`,
   `#ColdEmail`, `#LLMs`.
3. **Application** — the kind of work. `#AIAgents`, `#Automation`,
   `#GenerativeAI`, `#DataStrategy`.
4. **Audience** — who should see it. `#B2BSaaS`, `#PrivateEquity`, `#Founders`,
   `#AgencyLife`, `#GTM`.
5. **Angle** — the argument or theme. `#FutureOfWork`, `#ProductGrowth`,
   `#TechStrategy`, `#SalesOps`.

The failure to avoid, from the 2026-08-15 post: `#AI #ArtificialIntelligence
#AIAgents #Claude #ClaudeCode` — three near-duplicate AI tags and two Claude tags
on a post about Google Gemini. Five slots spent saying two things, one of them
wrong. That post ships as-is; the rule starts with the next one.

What it should have been: `#ArtificialIntelligence #Gemini #GenerativeAI
#ProductGrowth #FutureOfWork`.

Sanity check before returning a draft: read the five tags alone, with the post
hidden. Do they describe what the post is actually about, and does each one add
something the others don't? If two could be deleted without losing a signal, they
are the wrong two.

## The daily run — automated, weekdays

7:00am ET Monday to Friday, the run pulls the day's AI news, picks the two best
stories that are not already covered, drafts them, validates them, and schedules
them to publish at **8:30am and 2:30pm ET the same day**. Full procedure in
[docs/05-daily-run.md](docs/05-daily-run.md).

**Op-eds, live since 2026-09-14.** Monday to Thursday the 2:30pm post is an op-ed
instead of news, so the week is four op-eds and six news posts. The run uses John's
approved op-eds in [drafts/oped/queue/](drafts/oped/queue/) first. Once that queue
is empty, it writes new ones, but **only arguing the positions in
[docs/06-oped-themes.md](docs/06-oped-themes.md)**. Never invent an opinion for
John. Never state as fact that a named person did something dishonest or staged.

Supporting tools, all in the project root:
- `coverage.py` — ledger of what has been posted, so the run never repeats a story
- `validate_post.py` — hard gates: five hashtags, no duplicate-family tags, no em
  dashes, no closing question, a real number, sane length
- `publish_asset.py` — hosts a carousel PDF and its cover, and verifies HTTP 200
  before handing the URLs on
- `buffer_schedule.py` — creates the live scheduled post, and `--cancel`s it
- `buffer_status.py` — reads back the true status of any post

## Trigger: "AI stories"

When John says **"AI stories"**, come back with **five recent AI news stories** —
headline plus a two-line description each, with the date and source. Nothing else.
No drafts, no analysis, no recommendation of which to pick.

He picks one or more. Those become LinkedIn posts, as text or carousels, his call.

He may also hand over his own source ("turn this into a LinkedIn post"). Same
drafting rules either way.

## Hard rules

- **Auto-publishing is ON for the daily run, as of 2026-08-23.** John's decision,
  recorded here deliberately. The daily run creates *live scheduled* posts at
  8:30am and 2:30pm ET; the gate is the window before `dueAt`, and silence ships
  them. See [docs/05-daily-run.md](docs/05-daily-run.md).
- **Everything outside the daily run is still drafts only.** `buffer_draft.py`
  keeps `saveToDraft: true` and never publishes. Publishing requires
  `buffer_schedule.py`, which is a separate tool on purpose.
- **Kill a scheduled post** with `python3 buffer_schedule.py --cancel <post_id>`,
  any time before it fires.
- **Editing a draft in Buffer's own composer can flip it to `scheduled`.** Seen
  2026-08-15, and confirmed the hard way 2026-08-21: four drafts John opened in
  the composer to attach carousels went to `addToQueue` and published on their
  own, two of them on a Saturday. One published without its carousel attached.
  Re-read `status` after any round-trip through the UI with
  `python3 buffer_status.py <id>`. Better: attach carousels by URL through
  `publish_asset.py` so the composer never has to be opened.
- One Buffer draft per asset, so each can be killed independently.
- Never invent a number, client, outcome, or date. Never upgrade a story: if the
  card says six demos, the post says six, not "10x."
- **Story cards flagged PERSONAL** (S06 in the example bank) are never used
  without John clearing them for that specific piece.
- Never name a client who is not already named in the source.
- Never report a draft as pushed without confirming it in Buffer's response.

## Buffer mechanics (verified 2026-08-15)

The legacy REST API (`api.bufferapp.com`) rejects current API keys and retires
1 Feb 2027. Ignore any example written against it. Use the GraphQL endpoint:

```
POST https://api.buffer.com   Authorization: Bearer $BUFFER_ACCESS_TOKEN
```

`createPost(input:{channelId, text, assets, schedulingType: automatic,
mode: addToQueue, saveToDraft: true})`. Note `assets` is required — pass `[]` for
a text post. Carousels attach as `{document: {url}}` (LinkedIn carousels are PDFs).

Wrapper: [buffer_draft.py](buffer_draft.py). `python3 buffer_draft.py <file.md> [--due-at 2026-08-20T12:00:00Z] [--dry-run]`
`--due-at` sets the intended slot but leaves the post a draft; John promotes it.

Only one channel is connected: John's personal LinkedIn profile. No company pages.

## Carousels — in use

In production since 2026-08-17. He picks the format per post, or leaves it to you.
Best-sourced stories go to carousels: a frame has no room for a "reportedly", so a
story resting on second-hand numbers belongs in text where it can be hedged.

`python3 render_carousel.py carousels/<spec>.json` → a 1200x1500 PDF plus a cover
PNG in `build/`. Specs are JSON; frame types are `display`, `head`, `stat`. The
renderer enforces 4-or-6 frames and the 18-word limit and refuses to build
otherwise. Two worked examples are in [carousels/](carousels/).

Frames are typographic, not photographic. Chrome renders HTML/CSS to PDF so the
palette and type are exact — an image model cannot hold a hex value or spell a
headline. KIE.ai (`KIE_API_KEY`) is for photographic or illustrative imagery only,
never for frames with text on them.

Type is Playfair Display and Inter, both free Google Fonts, embedded from
`assets/fonts/` so the PDF renders identically on any machine.

### Getting a carousel into Buffer

Buffer posts LinkedIn PDF carousels fine. The only question is how the file
reaches Buffer.

**Manual route (outside the daily run): John drags the PDF in himself.** So when
he asks for a carousel ad hoc:

1. Render the PDF with `render_carousel.py`.
2. Create the accompanying **text draft** in Buffer with `buffer_draft.py` (no
   `--document`).
3. Hand him the PDF path and tell him to drag it into that draft's composer.

Do not attempt the API attachment route on this path — it cannot take a local
file.

**API route (used by the daily run):** the PDF and its thumbnail must sit at
public https URLs that stay reachable until the post publishes (no expiring or
signed links). `publish_asset.py` copies them into a static site and deploys it
with the Netlify CLI; the site checkout and its public URL come from
`ASSET_SITE_DIR`, `ASSET_PUBLISH_DIR` and `ASSET_BASE_URL` in `.env`.
`buffer_draft.py` and `buffer_schedule.py` take `--document --document-title
--thumbnail`, and enforce https plus the title LinkedIn requires. Limits:
under 300 pages, under 100MB.
