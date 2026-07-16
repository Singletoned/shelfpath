# Shelfpath follow-up

The initial design and shop-check functionality gaps have been completed.

## Completed functionality

- Series filter pills are server-driven links for All, Wanted (wanted but not owned), and Owned books.
- Shop check uses keyboard-friendly server-side fuzzy matching across titles, authors, and series names.
- Search results lead with a verdict card: **Wanted · buy it**, **Owned · skip**, or **Not on your want list**, followed by quieter secondary matches.
- On mobile, a fixed Shelf / Shop check / Lists tab bar keeps primary navigation within reach without expanding the header.
- Series source provenance is in a native disclosure so it does not delay access to books on a phone.
- Checking OWN or READ automatically unchecks WANT. WANT remains independently selectable afterward.

## Completed visual fixes

- Sort controls have a dark selected state; save actions are visibly heavier.
- Status chips have 44px touch targets and centered labels.
- Book numbers anchor to the title baseline rather than using a cover-centering offset.
- The progress track and cover placeholder use named palette variables.
- The owned-count pill uses a solid palette color.
- Shop series headings no longer inherit browser-default underlines, and the redundant page-level “Shelfpath” label is gone.
- Header links show the current page; its shop-check affordance is an explicit link/button rather than a fake text field.
- Main forms use the Shelfpath input, select, and textarea treatment.
- The desktop series page provides the specified series sidebar and two-column book layout.
