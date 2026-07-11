create table public.list_invitations (
    list_id uuid not null references public.lists(id) on delete cascade,
    email text not null,
    role public.list_member_role not null,
    invited_by_user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now(),
    primary key (list_id, email)
);

alter table public.list_invitations enable row level security;

drop policy if exists "owners can read list invitations" on public.list_invitations;
create policy "owners can read list invitations"
    on public.list_invitations for select
    to authenticated
    using (public.owns_list(list_id));

drop policy if exists "owners can remove list invitations" on public.list_invitations;
create policy "owners can remove list invitations"
    on public.list_invitations for delete
    to authenticated
    using (public.owns_list(list_id));

create or replace function public.add_list_member_by_email(
    target_list_id uuid,
    member_email text,
    member_role public.list_member_role default 'editor'
)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
    normalized_email text;
    target_user_id uuid;
begin
    normalized_email := lower(trim(member_email));

    if normalized_email = '' then
        raise exception 'Email address is required';
    end if;

    if member_role = 'owner' then
        raise exception 'Cannot grant owner role through sharing';
    end if;

    if not public.owns_list(target_list_id) then
        raise exception 'Only list owners can share lists';
    end if;

    select users.id into target_user_id
    from auth.users
    where lower(users.email) = normalized_email
    limit 1;

    if target_user_id is null then
        insert into public.list_invitations (list_id, email, role, invited_by_user_id)
        values (target_list_id, normalized_email, member_role, auth.uid())
        on conflict (list_id, email) do update
        set role = excluded.role,
            invited_by_user_id = excluded.invited_by_user_id;
        return;
    end if;

    insert into public.list_members (list_id, user_id, role)
    values (target_list_id, target_user_id, member_role)
    on conflict (list_id, user_id) do update
    set role = excluded.role;
end;
$$;

create or replace function public.accept_pending_list_invitations()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    insert into public.list_members (list_id, user_id, role)
    select list_invitations.list_id, new.id, list_invitations.role
    from public.list_invitations
    where lower(list_invitations.email) = lower(new.email)
    on conflict (list_id, user_id) do update
    set role = excluded.role;

    delete from public.list_invitations
    where lower(list_invitations.email) = lower(new.email);

    return new;
end;
$$;

drop trigger if exists accept_pending_list_invitations on auth.users;
create trigger accept_pending_list_invitations
after insert on auth.users
for each row execute function public.accept_pending_list_invitations();
