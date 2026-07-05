# Project Instructions

- The `data/` directory is its own git repository and is managed separately from this app repository.
- The parent app repository intentionally ignores `data/`; do not try to commit private catalogue data to the parent repository.
- When changing files under `data/`, also run git commands inside `data/` and make a separate commit there.
- Keep source/provenance notes for committed app-level documentation in the parent repository, and keep actual catalogue YAML/state changes in the `data/` repository.
- Manage Supabase schema changes with committed migrations under `supabase/migrations/` and automated commands such as `just db-push`; avoid manual dashboard SQL except for unavoidable one-time provider/account setup.
