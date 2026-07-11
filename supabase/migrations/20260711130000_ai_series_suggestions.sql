create type public.ai_series_suggestion_status as enum ('submitted', 'failed', 'approved', 'rejected');

create table public.ai_series_suggestion_allowed_users (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    email text,
    created_at timestamptz not null default now(),
    constraint ai_series_suggestion_allowed_users_has_identity check (user_id is not null or email is not null),
    constraint ai_series_suggestion_allowed_users_unique_user unique (user_id),
    constraint ai_series_suggestion_allowed_users_unique_email unique (email)
);

create table public.ai_series_suggestions (
    id uuid primary key default gen_random_uuid(),
    requested_by_user_id uuid not null references auth.users(id) on delete cascade,
    prompt text not null,
    status public.ai_series_suggestion_status not null,
    proposal jsonb,
    sources jsonb,
    error text,
    approved_series_id text references public.series(id) on delete set null,
    created_at timestamptz not null default now(),
    decided_at timestamptz
);

alter table public.ai_series_suggestion_allowed_users enable row level security;
alter table public.ai_series_suggestions enable row level security;

create or replace function public.can_use_ai_series_suggestions(target_user_id uuid default auth.uid())
returns boolean
language sql
security definer
set search_path = public, auth
stable
as $$
    select exists (
        select 1
        from public.ai_series_suggestion_allowed_users allowed
        join auth.users users on users.id = target_user_id
        where allowed.user_id = target_user_id
           or lower(allowed.email) = lower(users.email)
    );
$$;

create policy "allowed users can read their allow-list row"
    on public.ai_series_suggestion_allowed_users for select
    to authenticated
    using (public.can_use_ai_series_suggestions(auth.uid()));

create policy "allowed users can create own AI series suggestions"
    on public.ai_series_suggestions for insert
    to authenticated
    with check (requested_by_user_id = auth.uid() and public.can_use_ai_series_suggestions(auth.uid()));

create policy "users can read own AI series suggestions"
    on public.ai_series_suggestions for select
    to authenticated
    using (requested_by_user_id = auth.uid());

create or replace function public.count_ai_series_suggestions_today()
returns integer
language sql
security definer
set search_path = public
stable
as $$
    select count(*)::integer
    from public.ai_series_suggestions
    where requested_by_user_id = auth.uid()
      and created_at >= date_trunc('day', now());
$$;

grant execute on function public.count_ai_series_suggestions_today() to authenticated;

create or replace function public.reject_ai_series_suggestion(suggestion_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.ai_series_suggestions
    set status = 'rejected',
        decided_at = now()
    where id = suggestion_id
      and requested_by_user_id = auth.uid()
      and status = 'submitted';

    if not found then
        raise exception 'No submitted AI series suggestion % found for this user', suggestion_id;
    end if;
end;
$$;

grant execute on function public.reject_ai_series_suggestion(uuid) to authenticated;

create or replace function public.approve_ai_series_suggestion(suggestion_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    suggestion public.ai_series_suggestions%rowtype;
    proposed_series_id text;
    book jsonb;
begin
    select * into suggestion
    from public.ai_series_suggestions
    where id = suggestion_id
      and requested_by_user_id = auth.uid()
      and status = 'submitted';

    if not found then
        raise exception 'No submitted AI series suggestion % found for this user', suggestion_id;
    end if;

    if not public.can_use_ai_series_suggestions(auth.uid()) then
        raise exception 'This user is not allowed to approve AI series suggestions';
    end if;

    proposed_series_id := suggestion.proposal->>'series_id';
    if proposed_series_id is null or proposed_series_id = '' then
        raise exception 'AI series suggestion % has no series_id', suggestion_id;
    end if;

    insert into public.series (id, title, author, sort_order, source)
    values (
        proposed_series_id,
        suggestion.proposal->>'title',
        nullif(suggestion.proposal->>'author', ''),
        suggestion.proposal->>'order',
        suggestion.proposal->'source'
    );

    for book in select * from jsonb_array_elements(suggestion.proposal->'books') loop
        insert into public.books (series_id, book_id, title, position, author)
        values (
            proposed_series_id,
            book->>'id',
            book->>'title',
            (book->>'position')::integer,
            nullif(book->>'author', '')
        );
    end loop;

    update public.ai_series_suggestions
    set status = 'approved',
        approved_series_id = proposed_series_id,
        decided_at = now()
    where id = suggestion_id;
end;
$$;

grant execute on function public.approve_ai_series_suggestion(uuid) to authenticated;
