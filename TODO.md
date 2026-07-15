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
