# Feature: AI-assisted Series Suggestions

## Summary

Allow logged-in, allow-listed Shelfpath users to suggest a new book series or ordered collection. Shelfpath uses OpenAI to investigate the request, produce a proposed ordered list with provenance, show the AI-generated proposal for review, and let the same allowed user approve or reject it. Approved proposals are added directly to the live Supabase catalogue.

## Problem / Motivation

Adding catalogue data manually is tedious. Users should be able to request a series/list in natural language and let AI gather a draft list, while still requiring human review before it becomes part of the site.

## Goals

- Let selected trusted users request new series/list imports.
- Use AI to investigate web sources and produce a structured proposal.
- Show proposed books, ordering, warnings, and provenance before approval.
- Add approved proposals to the live Supabase catalogue.
- Keep audit/debug records for successful, rejected, and failed attempts.
- Add a hard usage limit to control cost and abuse.

## Non-goals

- No inline editing of AI proposals in the MVP.
- No duplicate detection or duplicate blocking yet.
- No background jobs yet; AI calls may be synchronous.
- No per-book provenance unless later experience shows it is needed.
- No automatic writes to the private `data/` repository.
- No public/admin discovery workflow for non-allowed users.

## Users / Actors

- **Logged-in user**: may or may not be allowed to use the feature.
- **Allowed suggester**: logged-in user whose account appears in a Supabase allow-list table.
- **OpenAI**: investigates the requested list and returns structured proposal data.
- **Shelfpath app**: validates permissions and rate limits, stores audit records, displays proposals, and imports approved catalogue data.

## Current Behavior

- Users can browse and update existing catalogue-backed lists.
- Series catalogue data lives in Supabase.
- Existing source/provenance can be stored on series.
- There is no in-app mechanism for suggesting or importing new series.
- There is no feature-specific allow list.

## Desired Behavior

1. An allowed user opens the series suggestion page.
2. The user enters a free-text request with optional helpful details such as:
   - series/list name,
   - desired ordering,
   - source hints,
   - author/publisher hints.
3. Shelfpath checks that the user is allow-listed and under the daily rate limit.
4. Shelfpath calls OpenAI synchronously to investigate the request.
5. Shelfpath stores the attempt and result, including failures.
6. The user sees an AI-generated proposal with:
   - series id,
   - title,
   - author,
   - order type,
   - source/provenance,
   - warnings or conflicts if any,
   - ordered books with position, title, and author.
7. The user approves or rejects the proposal.
8. Approval inserts the series and books into the Supabase catalogue immediately.
9. Rejection records status only and does not affect the catalogue.

## Preserve / Change / Remove

- **Preserve:** Supabase as the live production catalogue source of truth.
- **Preserve:** Existing series/book/provenance model where practical.
- **Preserve:** Human review before catalogue changes become visible.
- **Change:** Add an in-app trusted-user workflow for creating catalogue proposals.
- **Change:** Add audit/debug storage for proposal attempts and outcomes.
- **Remove:** Nothing currently; this is new functionality.

## Simplified Target

The MVP is a synchronous, allow-listed, approve/reject flow. It should be useful enough for trusted users without building a full admin console, editor, background job system, or duplicate-resolution workflow.

## Confirmed Decisions

- Allow list lives in Supabase, not committed config.
- Non-allowed logged-in users see a friendly message saying they should contact the site admin if they want access, without contact details.
- Users should be encouraged to provide as much useful context as they can.
- AI should investigate the web itself rather than only analyzing user-provided URLs.
- A “series” can be any sequence of books or book-like objects a user might want to collect or read in a particular order, including alternate orderings of the same books.
- If the user does not specify an order, default to publication order.
- If the user asks for another order, use that order.
- Review is approve/reject only for now.
- Approval immediately adds to the live Supabase catalogue.
- Store whatever provenance was used: primary/cross-check URLs, accessed date, and notes where available.
- UI must clearly state the proposal is AI-generated and should be reviewed.
- Duplicates are allowed until they become a practical problem.
- Failed attempts should be saved for debugging.
- Use OpenAI for the MVP.
- Calls may be synchronous.
- Rate limit is 5 suggestions per user per day.
- The same allow-listed user who requested a proposal may approve it.
- Rejected proposals are stored in the database for debugging/audit, but no full proposal history UI is required for MVP.
- OpenAI model should be configurable via env var, with `gpt-4.1-mini` as the default.
- If sources conflict, the proposal may show a warning and let the user decide.
- Production source of truth after approval is Supabase only.

## Acceptance Criteria

- Anonymous users are redirected to login before accessing the feature.
- Non-allowed logged-in users see the friendly access message.
- Allowed users can view and submit the suggestion form.
- Allowed users are limited to 5 suggestion attempts per day.
- AI output is stored with request, status, sources, warnings, and proposal JSON.
- Failed AI attempts are stored for debugging.
- Proposal page clearly says the content is AI-generated and requires review.
- Proposal includes series metadata, order type, provenance, warnings if any, and ordered books.
- Approving a proposal creates Supabase `series` and `books` records.
- Rejecting a proposal marks it rejected and does not create catalogue records.
- Duplicate series are not blocked in the MVP.
- OpenAI API key is configured by environment variable and is never committed.
- OpenAI model defaults to `gpt-4.1-mini` but can be overridden by environment variable.

## Examples / Scenarios

### Simple publication-order request

User enters:

```text
Rivers of London by Ben Aaronovitch
```

Shelfpath defaults to publication order, investigates likely sources, and returns a proposed ordered book list with provenance.

### Explicit alternate ordering request

User enters:

```text
Discworld chronological order, not publication order
```

Shelfpath asks AI for the requested chronological ordering and stores order/provenance notes explaining the source of that ordering.

### Publisher collection request

User enters:

```text
Penguin Modern Classics list, publisher order if available
```

Shelfpath treats the result as an ordered collection rather than a conventional narrative series.

### Non-allowed user

A logged-in user who is not in the allow list opens the suggestion page and sees a friendly access message. They cannot submit a suggestion.

### Failed investigation

OpenAI cannot find reliable sources or returns malformed data. Shelfpath records the failure for debugging and shows a clear error.

## Design Notes

- Add Supabase storage for:
  - allowed AI suggestion users,
  - suggestion attempts/proposals,
  - status transitions such as submitted, failed, approved, rejected.
- Use structured JSON from OpenAI if practical.
- Validate AI output before showing or importing it.
- Keep the UI explicit that AI output can be wrong.
- Store provenance at proposal/series level for MVP.
- Keep errors loud and actionable in development.
- Use Supabase row-level security/policies consistent with the existing app architecture.

## Alternatives Considered

- **Manual import only:** rejected because it does not solve the tedious catalogue-entry problem.
- **Require user-provided URLs only:** rejected for MVP because the desired workflow is for AI to investigate.
- **Background jobs:** deferred until synchronous calls prove insufficient.
- **Inline proposal editing:** deferred until it is clear how much editing is actually needed.
- **Duplicate blocking:** deferred until duplicates become a real problem.
- **Writing back to `data/`:** rejected for production because Supabase is now the live source of truth and production cannot sensibly write to the local private data repo.

## Risks / Unknowns

- AI may hallucinate, omit books, or choose poor sources.
- Web source quality and accessibility varies.
- Synchronous requests may be slow or time out for large/messy lists.
- OpenAI API failures need clear user-facing errors and stored debug records.
- Cost could grow if more users are allowed; rate limiting mitigates this.
- Duplicate catalogue entries may become confusing later.
- Source conflicts may require richer review tools later.
- Approval may fail partway through if database inserts are not atomic; implementation should avoid partial imports where possible.

## Rollout / Migration

- Add Supabase migrations for allow-listed users and proposal/audit storage.
- Configure Render/Shelfpath with:

```text
OPENAI_API_KEY
OPENAI_MODEL=gpt-4.1-mini
```

- Add at least one initial allowed user in Supabase.
- Deploy behind the allow list.
- Test with one or two known small/medium series before broader use.

## Testing Plan

- Unit tests for allow-list checks.
- Unit tests for per-user daily rate-limit logic.
- Unit tests for validating/parsing AI proposal JSON.
- Route tests for:
  - anonymous user redirect,
  - non-allowed user access message,
  - allowed user form access,
  - rate-limited user block,
  - proposal display,
  - approval imports catalogue rows,
  - rejection does not import rows.
- Mock OpenAI calls in automated tests.
- Database tests or integration-style tests for proposal approval/import behavior where practical.
- Manual live test with a known series and verified provenance.

## Open Questions

None for the MVP. Future questions include whether to add proposal editing, duplicate detection, background jobs, richer proposal history, or per-book provenance.
