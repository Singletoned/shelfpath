drop policy if exists "members can read lists" on public.lists;

create policy "members and owners can read lists"
    on public.lists for select
    to authenticated
    using (owner_user_id = auth.uid() or public.is_list_member(id));
