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
    select users.email::text, members.role, 'member'::text
    from public.list_members as members
    join auth.users as users on users.id = members.user_id
    where members.list_id = target_list_id
    union all
    select invitations.email, invitations.role, 'pending'::text
    from public.list_invitations as invitations
    where invitations.list_id = target_list_id
    order by 3, 1;
end;
$$;

create or replace function public.remove_list_person_by_email(
    target_list_id uuid,
    member_email text
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

    if not public.owns_list(target_list_id) then
        raise exception 'Only list owners can manage people';
    end if;

    select users.id into target_user_id
    from auth.users as users
    where lower(users.email) = normalized_email
    limit 1;

    if target_user_id = auth.uid() then
        raise exception 'Owners cannot remove themselves from their list';
    end if;

    delete from public.list_members
    where list_id = target_list_id
      and user_id = target_user_id;

    delete from public.list_invitations
    where list_id = target_list_id
      and lower(email) = normalized_email;
end;
$$;

grant execute on function public.list_people(uuid) to authenticated;
grant execute on function public.remove_list_person_by_email(uuid, text) to authenticated;
