drop trigger if exists accept_pending_list_invitations on auth.users;

create or replace function public.list_people(target_list_id uuid)
returns table (
    email text,
    role public.list_member_role,
    status text
)
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    if not public.owns_list(target_list_id) then
        raise exception 'Only list owners can manage people';
    end if;

    return query
    select users.email::text, members.role, 'active'::text
    from public.list_members as members
    join auth.users as users on users.id = members.user_id
    where members.list_id = target_list_id
    order by members.role, users.email;
end;
$$;

create or replace function public.set_list_member_role_by_email(
    target_list_id uuid,
    member_email text,
    member_role public.list_member_role
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

    if member_role = 'owner' then
        raise exception 'Cannot grant owner role through sharing';
    end if;
    if not public.owns_list(target_list_id) then
        raise exception 'Only list owners can manage people';
    end if;

    select users.id into target_user_id
    from auth.users as users
    where lower(users.email) = normalized_email
    limit 1;
    if target_user_id is null then
        raise exception 'No active Shelfpath member found for email %', normalized_email;
    end if;

    update public.list_members
    set role = member_role
    where list_id = target_list_id
      and user_id = target_user_id
      and role <> 'owner';

    if not found then
        raise exception 'No non-owner member found for email %', normalized_email;
    end if;
end;
$$;

grant execute on function public.set_list_member_role_by_email(uuid, text, public.list_member_role) to authenticated;
