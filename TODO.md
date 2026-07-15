# TODO — Implementation vs Design Conflicts

Issues where the current code contradicts or falls short of what DESIGN.md specifies.

## Filter pills on series detail are not interactive

DESIGN.md says: "Filter pills: All, Wanted, Owned." The word "filter" implies
they filter the book list. The implementation renders them as static `<span>`
elements that show counts but do nothing when tapped.

The data needed to filter is already present — hunting rows have the `hunting`
class, and chip state is in the HTML. These should be links or JS-driven
toggles that show/hide book rows.

This is the biggest usability gap given the app's core use case: standing in a
shop with a 41-book series, wanting to see only the books you're hunting for.

## Shop check search input does not function

DESIGN.md says: "Search should be prominent and keyboard-friendly" and "Fuzzy
matching across all series is expected when implemented."

The current implementation has an `<input type="search">` that accepts
keystrokes but does nothing. The help text says "Fuzzy title search is coming
next." A non-functional input that looks functional violates principle 6 ("Use
boring, visible controls") — it looks like a control but isn't one.

Either wire up client-side title filtering (the book titles are already in the
DOM) or remove the input until real search is ready.

## Shop check has no verdict cards

DESIGN.md says: "The top match should become a verdict card: orange WANTED /
buy, or dark OWNED · SKIP. Secondary matches are quieter dark cards."

The current implementation renders all wanted books as identical dark cards in a
flat list. There is no verdict distinction between a top match and secondary
results. This matters once search is functional — the first result should
visually answer "buy or skip?" immediately.

## Header search link is styled as a fake text input

DESIGN.md says: "cream search link to shop check." The design describes it as a
link. The implementation styles it as a cream-background box with a search icon
and placeholder-style text ("Check a book..."), making it look like a text
input. Users will try to type into it.

It should look like a link or button, not a text field.

---

# Visual bugs

## Sort buttons have no selected state

`.button.active` and `.button.secondary` are the same CSS rule (`base.html:299-303`),
so both sort buttons render as identical white pills with ink borders. There is
no way to tell which sort mode is currently selected.

The fix: remove `.button.active` from the `.button.secondary` rule. Then the
selected sort button gets the base `.button` style (dark fill) and the
unselected one gets `.secondary` (light outline).

## Sort toggle buttons and Save action button look like the same kind of control

On the series detail page, the sort toggles ("Series order" / "Alphabetical")
and the save action ("Save all changes") are all pill-shaped buttons with the
same sizing and border weight. They read as three buttons in the same family
rather than two distinct control types (toggle group vs form submit).

## Chip touch targets are below the 44px minimum

`.chip { min-height: 1.75rem }` at `base.html:411` is 28px. DESIGN.md says
"Keep minimum touch targets around 44px." The chips are the primary interaction
on both the series and shop pages.

## Book row number vertical alignment uses a magic padding value

`.book-number { padding-top: 1.35rem }` at `base.html:328` pushes the number
down to roughly center it against the cover image, but it doesn't align with
the title baseline or the cover top. The number floats at its own vertical
position, unrelated to anything else in the row.

## Progress track uses a hardcoded color

`.progress-track { background: #ede6d6 }` at `base.html:211` while every other
color in the system uses CSS variables from the defined palette.

## Cover placeholder gradient uses hardcoded hex values

`base.html:345-357` has raw hex colors `#e5dcc8` and `#f8efd9` instead of CSS
variables. These happen to correspond to palette values but bypass the variable
system.

## `.pill.own` uses rgba transparency instead of a solid palette color

`base.html:286` has `rgba(255, 248, 234, 0.18)` which renders differently
depending on what's behind it. Every other pill uses a solid color from the
palette.

## Shop page series headings are underlined

The `<h3><a>` links in `shop.html:19` inherit the browser-default underline.
Series headings on the home page use `.card h3 a { text-decoration: none }`.
The link treatment is inconsistent between pages.

## Shop page has redundant "Shelfpath" text

The shop page heading row (`shop.html:8`) places a faint "Shelfpath" label next
to "Shop check". The wordmark is already in the site header directly above.
This reads as leftover design artifact.
