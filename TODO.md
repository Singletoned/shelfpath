# TODO — Implementation vs Design Conflicts

Remaining functional gaps between the implementation and `DESIGN.md`.

## Filter pills on series detail are not interactive

DESIGN.md says: “Filter pills: All, Wanted, Owned.” The word “filter” implies
that they filter the book list. The implementation renders static `<span>`
elements that show counts but do nothing when tapped.

The data needed to filter is already present — hunting rows have the `hunting`
class, and chip state is in the HTML. These should be links or JS-driven
toggles that show or hide book rows.

This is the biggest usability gap given the core use case: standing in a shop
with a 41-book series and wanting to see only the books being hunted for.

## Shop check search input does not function

DESIGN.md says: “Search should be prominent and keyboard-friendly” and “Fuzzy
matching across all series is expected when implemented.”

The current `<input type="search">` accepts keystrokes but does nothing. The
help text says “Fuzzy title search is coming next.” A non-functional input that
looks functional violates principle 6 (“Use boring, visible controls”).

Either wire up client-side title filtering or remove the input until real search
is ready.

## Shop check has no verdict cards

DESIGN.md says: “The top match should become a verdict card: orange WANTED /
buy, or dark OWNED · SKIP. Secondary matches are quieter dark cards.”

The current implementation renders all wanted books as identical dark cards in
a flat list. There is no verdict distinction between a top match and secondary
results. Once search is functional, the first result should visually answer
“buy or skip?” immediately.

## Completed visual fixes

The following design-only work was completed in the current pass:

- Sort controls now have a dark selected state; save actions are visibly heavier.
- Status chips have 44px touch targets and centered labels.
- Book numbers now anchor to the title baseline rather than using a cover-centering offset.
- The progress track and cover placeholder use named palette variables.
- The owned-count pill now uses a solid palette color.
- Shop series headings no longer inherit browser-default underlines, and the redundant page-level “Shelfpath” label is gone.
- Header links now show the current page; its shop-check affordance is an explicit link/button rather than a fake text field.
- Main forms use the Shelfpath input, select, and textarea treatment.
- The desktop series page now provides the specified series sidebar and two-column book layout.
- Mobile header chrome has been reduced to the primary Shelf / Shop check path and sign-out control.
