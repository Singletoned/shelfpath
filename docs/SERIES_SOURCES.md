# Series Source Notes

These notes track candidate sources for sequence data. They are not imported book data; they are provenance and review notes for deciding what to import into private `data/` files.

Accessed: 2026-06-23

## Discworld

### Preferred source: official Terry Pratchett Books Discworld page

- URL: https://www.terrypratchettbooks.com/book-series/discworld/
- Source type: official author/estate/publisher site
- Useful for: Discworld title sequence in publication order
- Evidence found: the page says, “Below, you’ll find all 41 Discworld novels in the order they were published.”
- Extraction shape: the page renders a sequence of book cards. The visible card headings contain the book titles in order.
- Proposed use: primary source for title/order import.

### Cross-check source: Wikipedia Discworld page

- URL: https://en.wikipedia.org/wiki/Discworld
- Source type: community-maintained encyclopedia
- Useful for: numbered bibliography table, publication years, sub-series labels, and sanity checking the official page order
- Evidence found: the page has a `Bibliography > Novels` table beginning with:
  - 1. The Colour of Magic
  - 2. The Light Fantastic
  - 3. Equal Rites
  - 4. Mort
- Proposed use: cross-check source, not the primary source.

### Notes and review questions

- The MVP should import one publication-order Discworld list.
- Do not commit the resulting Discworld YAML; it belongs in private `data/`.
- Review whether to include only the 41 core novels, or also related Discworld works/short stories/maps/companions later. The official page's “all 41 Discworld novels” wording is the right MVP boundary.

## The Sandman

### Preferred source candidate: Wikipedia The Sandman page, collected editions section

- URL: https://en.wikipedia.org/wiki/The_Sandman_(comic_book)
- Source type: community-maintained encyclopedia
- Useful for: collected edition sequences and issue ranges
- Evidence found: the page has `Collected editions` sections including:
  - `Trade paperbacks`
  - `30th Anniversary editions`
  - `2022–2023 paperback reprints`
- The trade paperback section begins with:
  - Preludes and Nocturnes — collects The Sandman #1–8
  - The Doll's House — collects The Sandman #9–16
- The 30th Anniversary note says DC republished the previous ten trade paperbacks, plus Endless Nights as Volume 11, The Dream Hunters as separate unnumbered volumes, and Overture as Volume ∞.
- Proposed use: primary source for the initial Sandman collection import, because it distinguishes collection formats.

### Official source attempts

- Neil Gaiman official Sandman page
  - URL: https://www.neilgaiman.com/works/Comics/The+Sandman/
  - Result: accessible, but too sparse for sequence extraction.
- DC official pages
  - Example attempted URL: https://www.dc.com/graphic-novels/the-sandman-1989/the-sandman-vol-1-preludes-nocturnes-30th-anniversary-edition
  - Result: blocked with HTTP 403 during fetch.

### Notes and review questions

- The key question is which Sandman sequence to import first:
  1. Original ten trade paperback collections.
  2. 30th Anniversary editions: previous ten trade paperbacks plus Endless Nights as Volume 11, Dream Hunters as unnumbered, and Overture as Volume ∞.
  3. 2022–2023 `Book One` / `Book Two` style paperback reprints.
- For second-hand shopping, the best starting point is probably the format most likely to be found in charity shops. That may be the original/30th-anniversary volume naming rather than the newer `Book One` grouping.
- Do not commit the resulting Sandman YAML; it belongs in private `data/`.

## Proposed import approach after review

1. Extract candidate ordered titles from the preferred source.
2. Generate draft YAML privately under `data/series/`.
3. Review the draft manually before treating it as canonical.
4. Keep this source note updated with source URL, accessed date, and any judgement calls.
