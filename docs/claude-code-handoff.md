# Context handoff — content factory build

## What this is

> This is the original brief that started the project, kept for context. Some
> of it is now out of date (auto-publishing was later turned on for the daily
> run, and file 02 now holds a neutral system).

I'm building a personal content factory based on the "four files" pattern from a
content workshop I attended. The idea: turn
recordings and sources I already have into publishable content, using four
reusable files plus a worker skill. The machine does ~80%, my review is the last
5 minutes and the actual moat.

I built the four files in a Claude chat session. They're in this folder. Read all
four before doing anything.

## The four files

- **`01-voice-john.md`** — my voice, extracted from 13 of my real LinkedIn posts.
  Sound, phrases I use, point of view, never-use list, three reference paragraphs,
  and five checks a draft has to pass. Signature details: I use `--` not em dashes,
  I open with a claim not a setup, I use TLDR / hot take / FYI / IMO, and my posts
  end on a question to the room or a dry verdict, never a lesson.

- **`02-visual-design-system.md`** — palette, type scale, and layout rules for
  carousels. Currently populated with a borrowed placeholder brand. Swapping in my
  own system is a known TODO. The skill loads whatever is at this filename.

- **`03-story-bank-john.csv`** — story cards from an interview. Columns: id, type,
  what, detail, lesson, quote, pillar, source. Types are story / receipt / scar /
  take / analogy. Pillars are content themes (outbound, pricing, agency strategy,
  AI practice, personal, and so on).
  **Cards flagged PERSONAL are never used without me clearing them for that piece.**

- **`04-channel-skill-john.md`** — the worker. Loads the other three, takes one
  source, returns one LinkedIn text post and two carousels (4 or 6 frames), plus
  the story card ID used and a fact-check list. Drafts only. Never publishes.

## What already ran

I did one test run in chat, on this source: Google announced Aug 11 that Gemini
crossed 1 billion monthly active users — its fastest-growing product ever and 14th
to reach a billion; ChatGPT crossed the same mark in June.

Angle: Gemini is arguably the third or fourth best AI platform and still got to a
billion faster than anything Google has ever shipped, which says the demand isn't
at the frontier, it's everywhere. Matched to a story card about niching down
possibly being the wrong advice in the AI era.

The approved draft is in **`gemini-1b-post.md`** in this folder. It passed all five
voice checks. One fact-check note: "third or fourth best" is my opinion, not a
sourced claim, and is stated as opinion in the post.

## What I need you to do now

Post that draft to Buffer **as a draft**, not scheduled and not published.

1. Read `gemini-1b-post.md`.
2. Write a small, reusable script (`buffer-draft.js` or `.py`, your call) that
   creates a Buffer draft update via their API. It should take post text and an
   optional media path, and target my LinkedIn profile.
3. Read the Buffer access token from a `.env` file or the environment. **Never
   hardcode it, never echo it, never commit it.** Add `.env` to `.gitignore` if
   there isn't one.
4. Buffer's API has changed over time — check their current docs before writing
   against a remembered endpoint shape. Confirm the correct field for creating an
   unpublished draft rather than a queued or scheduled post.
5. Run it against the Gemini post. Report back the Buffer response, the draft ID,
   and confirm it is a draft in the queue and not live.
6. If the call fails, show me the error and the request you sent. Don't retry
   with different parameters until I've seen it.

Do not enable auto-posting. Drafts only until I explicitly change that.

## Known gaps, for your awareness

- No spacing scale, grid, corner radius, or icon rules in file 02 — carousel
  rendering isn't solved yet, only specified.
- The placeholder brand's fonts are licensed commercial fonts.
- Story bank is thin on receipts (hard numbers from my own client work). That's
  the weakest part of the system.
- File 04 has never been run end to end with real file loading. This is the
  first real test.
