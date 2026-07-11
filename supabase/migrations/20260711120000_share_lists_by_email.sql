create policy "owners can add list members"
    on public.list_members for insert
    to authenticated
    with check (public.owns_list(list_id));

create policy "owners can update list members"
    on public.list_members for update
    to authenticated
    using (public.owns_list(list_id))
    with check (public.owns_list(list_id));

create policy "owners can remove list members"
    on public.list_members for delete
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
    target_user_id uuid;
begin
    if member_role = 'owner' then
        raise exception 'Cannot grant owner role through sharing';
    end if;

    if not public.owns_list(target_list_id) then
        raise exception 'Only list owners can share lists';
    end if;

    select users.id into target_user_id
    from auth.users
    where lower(users.email) = lower(member_email)
    limit 1;

    if target_user_id is null then
        raise exception 'No Shelfpath user found for email %. Ask them to sign in once first.', member_email;
    end if;

    insert into public.list_members (list_id, user_id, role)
    values (target_list_id, target_user_id, member_role)
    on conflict (list_id, user_id) do update
    set role = excluded.role;
end;
$$;

grant execute on function public.add_list_member_by_email(uuid, text, public.list_member_role) to authenticated;
