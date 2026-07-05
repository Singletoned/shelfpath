# Implementation Plan

## Project Context

Shelfpath is a mobile-friendly tracker for ordered book series and shared collecting lists. Its primary purpose is to help while browsing second-hand book shops: quickly answer whether a book is already owned, whether it has been read, and where it sits in a series.

The first useful milestone is:

> I can import Discworld/Sandman-style ordered lists, mark books as owned/read, and check missing books on my phone.

## Current State

The repository currently contains:

- A small Starlette app in `app.py`.
- Basic Jinja templates in `templates/`.
- An experimental barcode/image upload flow using `pyzbar` and Pillow.
- `PROJECT.md` describing the durable product direction.

The barcode flow is useful later, but it should not drive the MVP.

## Target Outcome

The MVP should:

- Treat lists/series as the main user experience.
- Load ordered book lists from human-editable YAML.
- Store ownership/read state in human-editable YAML for the current local implementation.
- Keep all real user data out of git.
- Let the user mark books as owned and/or read.
- Provide a shop-focused view of books not currently owned.
- Be simple enough to trial before committing to deployment, sync, offline, or export decisions.

## Planning Assumptions and Decisions

- Keep Starlette where useful; replace code that no longer serves the MVP.
- Use YAML files for data because the dataset is small and manually maintained.
- Do not commit personal book data, user state, databases, or generated runtime data.
- Commit only examples/templates such as `data.example/`.
- Gitignore the real `data/` directory in the app repository.
- Treat `data/` as its own separately committed repository when present.
- Focus on `owned` and `read`; ignore explicit `wanted` for now.
- `read: true` while `owned: false` is valid because read books may have been given away.
- Barcode/ISBN scanning is not part of the MVP.
- Authentication, hosting, backup, sync, and offline-first behaviour will be replanned after the app is useful locally.
- Static export should be usage-led. Build `/shop` first, try it, then decide whether static HTML, Markdown, Reminders, or a served web app is the right phone workflow.
- Use `unittest` for focused automated tests, but prioritise manual/browser testing during this exploratory phase.

## Data Layout

Commit example data only:

```text
data.example/
  series/
    example-series.yaml
  state.yaml
```

Gitignore private user data:

```text
data/
```

Actual local data should live in:

```text
data/
  series/
    discworld.yaml
    sandman.yaml
  state.yaml
```

Example series file:

```yaml
id: example-series
title: Example Series
author: Example Author
order: publication
books:
  - id: first-book
    title: First Book
    position: 1
  - id: second-book
    title: Second Book
    position: 2
```

Example state file:

```yaml
books:
  example-series/first-book:
    owned: true
    read: true
  example-series/second-book:
    owned: false
    read: true
```

## Phase 1: YAML-backed Series Checklist

### Goal

Replace the barcode-first prototype with the core app: ordered series pages with persistent owned/read tracking.

### Dependencies

- Add YAML parsing support, likely `pyyaml`.
- Keep Starlette/Jinja unless a concrete reason to change appears.
- Add private data handling before adding real book lists.

### Concrete Tasks

1. Add YAML support to `requirements.txt`.
2. Add `data/` to `.gitignore`.
3. Add committed example files under `data.example/`.
4. Document how to copy `data.example/` to `data/` for local use.
5. Create a small library module for loading catalogue data.
6. Load every `data/series/*.yaml` file.
7. Load `data/state.yaml`.
8. Merge series definitions with personal state.
9. Validate required fields:
   - series `id`
   - series `title`
   - book `id`
   - book `title`
10. Fail loudly on malformed YAML, missing required fields, duplicate series IDs, or duplicate book IDs.
11. Preserve unknown state entries by warning rather than silently deleting them.
12. Implement state saving for `owned` and `read`.
13. Regenerate clean YAML when writing state; preserving YAML comments is not required.
14. Replace the homepage with a series list showing owned/read progress.
15. Add a series detail page showing books in order.
16. Add controls to mark each book owned and/or read.
17. Ensure read-but-not-owned books are displayed as valid, not erroneous.
18. Move the existing barcode upload out of the main flow or remove it until the scanning phase.
19. Update `README.md` with setup, data format, and manual usage instructions.

### Definition of Done

- The app starts successfully with valid local data.
- The app loads private YAML data from `data/`.
- `data/` is gitignored.
- Example data is committed under `data.example/`.
- The homepage lists available series.
- A series page shows books in order.
- Owned/read state can be changed in the browser.
- State persists across refreshes and app restarts.
- Read-but-not-owned books are allowed.
- Broken YAML or duplicate IDs produce clear, actionable errors.

## Phase 2: Shop Use Workflow

### Goal

Make the app useful while standing in a second-hand book shop.

### Dependencies

- Phase 1 data loading and state saving must be stable.
- The app should already know which books are owned.
- The phone workflow should be trialled before building export/sync features.

### Concrete Tasks

1. Add `GET /shop`.
2. Show all not-owned books grouped by series.
3. Preserve each series' configured order.
4. Show enough context to identify a book quickly: title, series, position, and author where available.
5. Optimise the layout for phone-sized screens:
   - large tap targets
   - compact vertical layout
   - readable typography
   - minimal clutter
6. Add simple client-side filtering if it helps real use.
7. Make missing books easy to scan visually.
8. Trial the workflow locally and, if practical, from Safari on the phone.
9. Decide the actual phone consumption path after the trial:
   - served web app
   - static HTML
   - Markdown checklist
   - iOS Reminders
   - another approach
10. Do not build static export until the intended usage pattern is clearer.

### Definition of Done

- `/shop` lists not-owned books grouped by series.
- Owned books are omitted from `/shop`.
- Read-but-not-owned books still appear as not owned.
- The shop view is usable on a phone-sized screen.
- There is enough real usage feedback to choose the next phone/sync/export approach.

## Later Phases

### Editing and Import UI

- Add UI to create and edit series.
- Add YAML upload/import.
- Add validation preview before accepting imported data.
- Add duplicate detection and helpful import errors.

### Static, Markdown, or Phone Export

- If static HTML proves useful, generate a small read-only export.
- If Markdown is easier to consume, generate checklist-style Markdown.
- If Reminders is better, investigate export/sync options.
- Keep this usage-led rather than production-led.

### Barcode and ISBN Scanning

- Revisit the existing `pyzbar` experiment.
- Add optional ISBN fields to YAML only when needed.
- Decide whether scanning should be server-side image upload, browser-side camera scanning, or native app functionality.
- Match scanned ISBNs against known books and report whether the book is owned, missing, part of a tracked series, or unknown.

### Backup, Sync, Offline, and Deployment

- Replan once the local app is useful.
- Consider iCloud-synced files, static exports, private hosting, or PWA/offline-first behaviour.
- Add authentication before exposing the app beyond a trusted local network.

## Testing and Validation

### Automated Tests

Use focused `unittest` coverage for:

- Loading valid series YAML.
- Rejecting malformed YAML.
- Rejecting missing required fields.
- Rejecting duplicate series IDs and duplicate book IDs.
- Merging series data with state.
- Saving state without losing unrelated entries.
- Computing owned/read/missing counts.
- Allowing `read: true` while `owned: false`.

### Manual Browser Checks

Maintain a short manual checklist:

1. Start the app.
2. Open the homepage.
3. Open a series page.
4. Mark a book owned.
5. Mark a book read.
6. Refresh and confirm state persisted.
7. Restart the app and confirm state persisted.
8. Open `/shop`.
9. Confirm owned books are omitted from `/shop`.
10. Confirm read-but-not-owned books are still shown as not owned.
11. Intentionally break YAML and confirm the error is obvious.
12. Check the main views at phone-sized browser widths.

Browser automation can be added later when the UI stabilises.

## Risks and Mitigations

### Personal data accidentally committed

Mitigation:

- Gitignore `data/` immediately.
- Commit only `data.example/`.
- Document the distinction clearly in `README.md`.
- Never commit databases or generated personal state.

### YAML schema churn

Mitigation:

- Keep the schema small at first.
- Validate loudly.
- Document examples.
- Avoid adding fields until the app needs them.

### State gets out of sync with series files

Mitigation:

- Use stable keys like `series_id/book_id`.
- Warn on unknown state entries.
- Do not silently delete unknown state.

### Wrong phone workflow

Mitigation:

- Build `/shop` first.
- Trial real usage.
- Choose export/sync/deployment based on that experience.

### Barcode work distracts from MVP

Mitigation:

- Remove it from the main flow.
- Treat scanning as a later phase.

## Open Questions

- What is the easiest reliable way to consume the shop list on an iPhone?
- Should the first phone workflow be a served web app, static HTML, Markdown, Reminders, or something else?
- How much edition metadata is needed before the app becomes too close to a full bibliographic database?
- Which external metadata sources, if any, are worth integrating during the scanning phase?

## Immediate Next Step

Implement Phase 1: YAML-backed series checklist, starting with private data handling, example data, loader validation, and the series detail UI.
