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
- Chips are pills, never circles: 1.5px border, 10.5–12.5px/800 text, and about 5px vertical by 7–9px horizontal padding. The visual chip row must remain lighter than a primary action button; an invisible label hit target may supply the 44px touch area.

## Screens

### Public landing / sign in

- Anonymous visitors see a compact, single-purpose splash page at `/`, not a redirect to a separate sign-in screen.
- The page states the shop-check benefit first, then explains only three practical tasks: series position, book status, and shared lists.
- The email magic-link form is part of the page and explicitly serves both sign-in and account creation. Do not imply a separate password registration flow.
- Avoid product screenshots, generic feature-card grids, and social proof: this is a personal utility, so a clear benefit and immediate email action are more useful.

### Shelf / Home

- Orange header with the Shelfpath book-mark icon immediately before the Shelfpath wordmark and a cream search link to shop check.
- Body overline: “MY SERIES”.
- Series cards: paper background, light border, 14px radius, 16px padding. The whole card is the link to the series; do not make only its title clickable.
- Card shows title, author, wanted count in orange, stacked progress bar, and small legend.
- Progress colors: read = blue, owned-unread = ink, track = light cream.
- **Next up:** on desktop, show a narrow right-hand list for the active Shelfpath list; on mobile it follows the series cards. An entry is eligible only when it is owned and unread _and_ every lower-positioned book in that series is marked read. This produces at most one next-up book per series, never recommends a book out of sequence, and permits earlier books read without ownership. The only status control in this list is the READ pill, which saves immediately.

### Series detail

- Ink header with back link, title, author/order metadata, and filter pills.
- Filter pills: All, Wanted, Owned. Unselected pills are transparent with a cream outline/text; selection uses cream fill with ink text. Wanted uses orange with cream text only when selected as its semantic accent.
- Rows use the core row anatomy above.
- Sort controls remain visible and ordinary.
- Status chips persist automatically and show brief save feedback; no separate Save action is shown.

### Shop check

- Dark ink page.
- Search should be prominent and keyboard-friendly.
- The top match should become a verdict card: orange WANTED / buy, or dark OWNED · SKIP.
- Secondary matches are quieter dark cards.
- Fuzzy matching across all series is expected when implemented.

### Desktop

- Orange top nav with Shelf, Suggest series, a “Check a book…” search field, and an account avatar. Each destination appears once: Shop check is entered by that field on desktop and by the mobile tab on mobile; never add a second Shop check link.
- The account control is an ink avatar circle with a cream initial. Reveal email and sign-out in its menu; never show the raw email in chrome.
- Use a two-column layout when space allows: series sidebar + main content.
- Sidebar anatomy: active series has ink fill, cream text, and an orange wanted-count badge. Inactive series has ink text and a neutral badge. Replace the badge with ✓ when every book is owned.
- Book rows can become two-column cards but must keep the same anatomy and semantics.

## Covers

Use Open Library Covers API as the first cover source.

- Store Open Library `cover_i` IDs when available.
- Render covers from `https://covers.openlibrary.org/b/id/{cover_id}-M.jpg` for row/list covers.
- Do not block rendering on cover lookups; text and chips should appear first.
- If no cover ID exists, show the striped placeholder.
- Attribute in the UI: “Some covers provided by Open Library.”

## Controls

Distinguish visually between toggle controls and action buttons:

- **Toggle group** (e.g. sort order): the selected option should be filled/dark, unselected options should be light/outline. The group should read as "pick one of these."
- **Action button** (e.g. Save): should look heavier or more prominent than toggles. It commits a change rather than switching a view.

These should not share the same visual treatment. If they all look the same, users cannot tell which controls change the view and which submit data.

## Colors

All colors in CSS should reference the CSS custom properties defined in `:root`. Do not use hardcoded hex or rgba values — they bypass the palette and drift silently when the palette changes.

## Book row number alignment

The row number should align to the first baseline of the book title, not float at an arbitrary vertical offset. Use baseline alignment rather than a magic `padding-top` value that approximates cover-centering.

## Save feedback

- Status chips save immediately. Show a brief inline saving/saved confirmation and restore the previous state with an actionable error if persistence fails.
- Disable a row’s chips while its update is in flight so rapid taps cannot overwrite a newer state with an older request.

## Form elements

Text inputs, textareas, and selects (used on the login, lists, and suggest pages) should be styled consistently with the rest of the app: matching border radius, padding, font, and color tokens. Browser-default form elements break the visual coherence. The login form stays within a readable 32rem column, with deliberate gaps between its introduction, field, submit action, and feedback.

## Navigation

- The current page must have an active state in the nav. Series detail belongs to Shelf.
- On mobile, the header should be as compact as possible. The critical use case is "under ten seconds on a phone" — every row of chrome above the content costs time. Account controls and secondary links should not push content below the fold.
- Screen headers contain at most a wordmark/back link, title, one metadata line, and one pill row. Remove empty vertical space rather than filling it.

## Metadata hygiene

Book metadata is author and/or year only. Strip publisher blurbs, biographies, and subtitle marketing during catalogue import; do not try to conceal dirty metadata at render time.

## Implementation notes

- `want`, `owned`, and `read` are independent booleans.
- `missing` / `hunting` is derived: `want && !owned`.
- `give away` is derived: `owned && read`; add as a filter later if it becomes useful.
- Avoid avatars, presence indicators, and activity feeds for shared lists.
- Keep minimum touch targets around 44px.
