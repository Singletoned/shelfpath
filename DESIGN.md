# Shelfpath Design Guide

Shelfpath is for checking ordered book lists quickly in second-hand shops. The critical moment is: a user is holding a book, does not know its place in a series, and needs to know whether to buy it in under ten seconds on a phone.

This guide is based on the design handoff in `/Users/singletoned/Downloads/design_handoff_shelfspace/README.md` and the canonical screens in `Shelfpath Screens.dc.html`, especially turns 4 and 5. Earlier turns are historical and should not be reintroduced.

## Principles

1. **Utility first, branding second.** Color carries meaning before decoration.
2. **Missing books lead.** The app is about books the user is hunting for, not books already on the shelf.
3. **Statuses are independent booleans.** `want`, `own`, and `read` are separate flags. Do not turn them into one lifecycle enum.
4. **Covers stay visible.** Missing books must still show covers because covers help recognition in shops.
5. **Chips are the status source of truth.** Do not add extra prose such as “owned/unread” or “read a library copy”.
6. **Use boring, visible controls.** Search fields, list rows, buttons, and chips are preferred over gestures or hidden interactions.
7. **Shop check is verdict-first.** It should answer “buy or skip?” before acting like a generic search result page.
8. **Sharing is setup.** Shared lists are practical configuration, not a social/activity surface.

## Color semantics

- Orange `#E85D1F`: WANT, hunting, buy verdicts, wanted counts. Also used for brand chrome.
- Ink `#17130C`: OWNED in light mode, primary text, dark surfaces.
- Blue `#3D6B9E`: READ.
- Cream `#FFF8EA`: app background and text on dark/colored surfaces.
- Paper `#FFFFFF`: cards and normal rows.
- Light border `#E5DCC8`; strong border `#C9BFA8`.
- Muted text `#6B6152`; faint text `#9A8F7C`; off-chip text `#B4A98F`; off-chip border `#DFD5BE`.
- Hunting row: `#FDEFE5` background and `#F5DCC8` border.
- Dark cards: `#221D13`; dark borders `#2C2619` / `#3A3325`.

Never use orange for a data state unless it means WANT/hunting, except for app chrome.

## Typography

Use Archivo, weights 400–900.

- Wordmark: 22–26px, weight 900, slight negative tracking.
- Screen titles: 21–22px, weight 900.
- Desktop page titles: 30px, weight 900.
- Row titles: 15px, weight 700, allow two lines.
- Card titles: 17px, weight 800.
- Metadata: 12–13px, weight 600.
- Overlines: 12–13px, weight 800, uppercase, letter spacing `0.1em`.
- Chips: 10.5–12.5px, weight 800.

## Core book row anatomy

Reuse this layout wherever books appear:

- Number: plain grey text, right-aligned, 22px column. Never a badge.
- Cover: 2:3 aspect ratio, rounded 4px, bordered. Always render either a real cover or a striped placeholder.
- Title: ink, bold, up to two lines.
- Metadata: factual only, such as author or year.
- Status chips: WANT · OWN · READ, in that order.
- Hunting rows (`want && !own`) get orange-tinted background. Normal rows stay quiet.

## Status chips

- Filled chip = on.
- Ghost outline chip = off.
- WANT on: orange fill, cream text.
- OWN on: ink fill, cream text.
- READ on: blue fill, cream text.
- Off: transparent, ghost text, off-chip border.

## Screens

### Shelf / Home

- Orange header with Shelfpath wordmark and cream search link to shop check.
- Body overline: “MY SERIES”.
- Series cards: paper background, light border, 14px radius, 16px padding.
- Card shows title, author, wanted count in orange, stacked progress bar, and small legend.
- Progress colors: read = blue, owned-unread = ink, track = light cream.

### Series detail

- Ink header with back link, title, author/order metadata, and filter pills.
- Filter pills: All, Wanted, Owned.
- Rows use the core row anatomy above.
- Sort controls remain visible and ordinary.
- Save controls should be easy to find at both top and bottom until optimistic chip persistence exists.

### Shop check

- Dark ink page.
- Search should be prominent and keyboard-friendly.
- The top match should become a verdict card: orange WANTED / buy, or dark OWNED · SKIP.
- Secondary matches are quieter dark cards.
- Fuzzy matching across all series is expected when implemented.

### Desktop

- Orange top nav with Shelf, Shop check, Import/Suggest, account controls.
- Use a two-column layout when space allows: series sidebar + main content.
- Book rows can become two-column cards but must keep the same anatomy and semantics.

## Covers

Use Open Library Covers API as the first cover source.

- Store Open Library `cover_i` IDs when available.
- Render covers from `https://covers.openlibrary.org/b/id/{cover_id}-M.jpg` for row/list covers.
- Do not block rendering on cover lookups; text and chips should appear first.
- If no cover ID exists, show the striped placeholder.
- Attribute in the UI: “Some covers provided by Open Library.”

## Implementation notes

- `want`, `owned`, and `read` are independent booleans.
- `missing` / `hunting` is derived: `want && !owned`.
- `give away` is derived: `owned && read`; add as a filter later if it becomes useful.
- Avoid avatars, presence indicators, and activity feeds for shared lists.
- Keep minimum touch targets around 44px.
