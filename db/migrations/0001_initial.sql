create table users (
    clerk_user_id text primary key,
    email text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table series (
    id text primary key,
    title text not null,
    author text,
    sort_order text,
    source jsonb,
    created_at timestamptz not null default now()
);

create table books (
    id uuid primary key default gen_random_uuid(),
    series_id text not null references series(id) on delete cascade,
    book_id text not null,
    key text generated always as (series_id || '/' || book_id) stored unique,
    title text not null,
    position integer not null,
    author text,
    openlibrary_cover_id integer,
    created_at timestamptz not null default now(),
    unique (series_id, book_id)
);

create type list_member_role as enum ('owner', 'editor', 'viewer');

create table lists (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_clerk_user_id text not null references users(clerk_user_id) on delete cascade,
    created_at timestamptz not null default now()
);

create table list_members (
    list_id uuid not null references lists(id) on delete cascade,
    clerk_user_id text not null references users(clerk_user_id) on delete cascade,
    role list_member_role not null,
    created_at timestamptz not null default now(),
    primary key (list_id, clerk_user_id)
);

create table book_states (
    list_id uuid not null references lists(id) on delete cascade,
    book_id uuid not null references books(id) on delete cascade,
    owned boolean not null default false,
    read boolean not null default false,
    wanted boolean not null default true,
    updated_at timestamptz not null default now(),
    primary key (list_id, book_id)
);

create table ai_series_suggestion_allowed_users (
    clerk_user_id text primary key references users(clerk_user_id) on delete cascade,
    created_at timestamptz not null default now()
);

create type ai_series_suggestion_status as enum ('pending', 'approved', 'rejected', 'failed');

create table ai_series_suggestions (
    id uuid primary key default gen_random_uuid(),
    requested_by_clerk_user_id text not null references users(clerk_user_id) on delete cascade,
    prompt text not null,
    status ai_series_suggestion_status not null default 'pending',
    proposal jsonb,
    source_urls jsonb,
    failure_message text,
    approved_series_id text references series(id) on delete set null,
    created_at timestamptz not null default now(),
    decided_at timestamptz
);

create index books_series_position_idx on books(series_id, position);
create index list_members_clerk_user_id_idx on list_members(clerk_user_id);
create index book_states_list_id_idx on book_states(list_id);
create index ai_suggestions_requester_created_idx
    on ai_series_suggestions(requested_by_clerk_user_id, created_at desc);

create or replace function set_updated_at() returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger users_set_updated_at before update on users
for each row execute function set_updated_at();

create trigger book_states_set_updated_at before update on book_states
for each row execute function set_updated_at();
