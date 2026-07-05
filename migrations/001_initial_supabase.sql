create extension if not exists pgcrypto;

create table public.series (
    id text primary key,
    title text not null,
    author text,
    sort_order text,
    source jsonb,
    created_at timestamptz not null default now()
);

create table public.books (
    id uuid primary key default gen_random_uuid(),
    series_id text not null references public.series(id) on delete cascade,
    book_id text not null,
    key text generated always as (series_id || '/' || book_id) stored unique,
    title text not null,
    position integer not null,
    author text,
    created_at timestamptz not null default now(),
    unique (series_id, book_id)
);

create table public.lists (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    owner_user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create type public.list_member_role as enum ('owner', 'editor', 'viewer');

create table public.list_members (
    list_id uuid not null references public.lists(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role public.list_member_role not null,
    created_at timestamptz not null default now(),
    primary key (list_id, user_id)
);

create table public.book_states (
    list_id uuid not null references public.lists(id) on delete cascade,
    book_id uuid not null references public.books(id) on delete cascade,
    owned boolean not null default false,
    read boolean not null default false,
    updated_at timestamptz not null default now(),
    primary key (list_id, book_id)
);

create or replace function public.is_list_member(target_list_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
    select exists (
        select 1 from public.list_members
        where list_members.list_id = target_list_id
          and list_members.user_id = auth.uid()
    );
$$;

create or replace function public.can_edit_list(target_list_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
    select exists (
        select 1 from public.list_members
        where list_members.list_id = target_list_id
          and list_members.user_id = auth.uid()
          and list_members.role in ('owner', 'editor')
    );
$$;

create or replace function public.owns_list(target_list_id uuid)
returns boolean
language sql
security definer
set search_path = public
stable
as $$
    select exists (
        select 1 from public.lists
        where lists.id = target_list_id
          and lists.owner_user_id = auth.uid()
    );
$$;

alter table public.series enable row level security;
alter table public.books enable row level security;
alter table public.lists enable row level security;
alter table public.list_members enable row level security;
alter table public.book_states enable row level security;

create policy "authenticated users can read series"
    on public.series for select
    to authenticated
    using (true);

create policy "authenticated users can read books"
    on public.books for select
    to authenticated
    using (true);

create policy "members can read lists"
    on public.lists for select
    to authenticated
    using (public.is_list_member(id));

create policy "users can create their own lists"
    on public.lists for insert
    to authenticated
    with check (owner_user_id = auth.uid());

create policy "members can read memberships"
    on public.list_members for select
    to authenticated
    using (public.is_list_member(list_id));

create policy "users can add themselves as owner to their own list"
    on public.list_members for insert
    to authenticated
    with check (user_id = auth.uid() and role = 'owner' and public.owns_list(list_id));

create policy "members can read book states"
    on public.book_states for select
    to authenticated
    using (public.is_list_member(list_id));

create policy "owners and editors can insert book states"
    on public.book_states for insert
    to authenticated
    with check (public.can_edit_list(list_id));

create policy "owners and editors can update book states"
    on public.book_states for update
    to authenticated
    using (public.can_edit_list(list_id))
    with check (public.can_edit_list(list_id));

create or replace function public.set_book_states_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

create trigger set_book_states_updated_at
before update on public.book_states
for each row execute function public.set_book_states_updated_at();
