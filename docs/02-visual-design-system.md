# Visual content design system

The palette, type and layout rules for carousels. `render_carousel.py` reads its
values from this file's decisions; nothing in the renderer invents a color or a
font. Rules not yet tested on a real published asset are marked **[PROPOSED]**.

## Recognition goal

Someone should recognize the post before they read the name.
The carrier is a large serif set at regular weight on a warm off-white field,
with a single blue as the only saturated color and a small uppercase
letterspaced eyebrow above. Most of the feed is loud; this is quiet on purpose.

## Palette

- Ink: `#111418` (near-black, the text color)
- Muted: `#8A8F98` (secondary text, eyebrows, counters)
- Accent: `#2F6FEB` (the one saturated color: stat numbers, panel eyebrows)
- Paper: `#F5F3EE` (warm off-white, the default surface)
- Tint: `#EAE7E0` (a step darker than paper, for body-copy frames that need separation)
- Band: `#DFE7F8` (accent at low saturation, carries stat blocks)
- Panel: `#111418` (ink used as a full-bleed closing frame)
- Lines: `#D6D3CC` (hairlines on paper), `#2A2F36` (hairlines on the panel)

Never use pure black `#000000` for text, and never use a second saturated color.

## Type rules

Both families are free Google Fonts (SIL Open Font License), embedded from
`assets/fonts/`.

- Display: Playfair Display, weight **400**, letter-spacing `0.25px`. Regular weight at large size is the whole identity. Do not bold it.
- Section head: Playfair Display 400, line-height 1.2.
- Body: Inter 400, line-height 1.5, letter-spacing `0.2px`.
- Eyebrow: Inter 600, uppercase, letter-spacing `1.8px` at carousel scale.
- Micro label: Inter 500, uppercase, letter-spacing `1.5px` at carousel scale.
- Stat number: Playfair Display 400, line-height 1.0, letter-spacing `-0.25px`, in accent.
- **Hierarchy comes from size and font-switching, never from bolding.** This is the rule most likely to be broken by a designer working fast.
- Two families only. Never fall back to a bare `sans-serif`; the fonts are embedded so the PDF is exact.

## Carousel scale

Frames are 1200x1500. Sizes in px: display 116, head 72, stat 240, body 34,
eyebrow 24, micro 20. Ratios matter more than absolutes; a carousel is read at
roughly a third of its native size on a phone.

## Layout rules

- Paper is the default field. Ink is a panel, not a background.
- Uppercase eyebrow, then the serif line beneath it, then generous space. That stack is the recognizable unit.
- One idea per frame.
- Left-aligned, with the display line allowed to run long across two or three lines.
- Band frames (`#DFE7F8`) carry stat blocks. A large accent-blue serif number on the band is the most repeatable composition in the system.
- Hairlines are `#D6D3CC`.

## Recurring devices

- **The uppercase eyebrow.** On every frame, muted gray, tracked.
- **The stat band.** Band field, oversized serif number in accent, small sans label beneath.
- **The ink panel.** `#111418` full-bleed frame with paper-colored type and an accent eyebrow, used for the closing frame.
- **The frame counter.** Micro label bottom-left, `01 / 06`.

## Three repeatable carousel formats **[PROPOSED]**

1. **The stat run.** Each frame is one number on the band with a one-line label.
2. **The thesis.** Frame 1 is a serif display claim on paper; frames 2 to 5 are body copy on paper or tint; frame 6 inverts to the ink panel.
3. **The company note.** Section-head serif plus small sans body, one company or theme per frame.

## Frame backgrounds in a spec

`render_carousel.py` accepts these `bg` values: `paper` (default), `tint`,
`band`, `panel`.

## Never use

- Bold serif display. The display face renders at 400 and that restraint is the system.
- More than two type families.
- A second saturated color, or the accent as a page background.
- Ink as a page background outside the closing panel.
- Pure black `#000000` for text. Ink is `#111418`.
- Stock photography, gradients, glossy mockups, or floating 3D objects.
- More than 18 words on a carousel frame.

## Recognition test

Hide the name. If the uppercase tracked eyebrow, the regular-weight serif
display, and a single blue element are all present on paper, it still reads as
this system. If the display line is bolded or the field is any color other than
paper, tint, band or ink, the frame is off-system.

## Known gaps

- No spacing scale, grid, corner radius, icon style, or photography direction yet.
- No logo lockup or clear-space rules.
