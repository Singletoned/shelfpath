grant usage on schema public to anon, authenticated, service_role;

grant select on public.series to authenticated;
grant select on public.books to authenticated;
grant select, insert on public.lists to authenticated;
grant select, insert on public.list_members to authenticated;
grant select, insert, update on public.book_states to authenticated;

grant select, insert, update, delete on public.series to service_role;
grant select, insert, update, delete on public.books to service_role;
grant select, insert, update, delete on public.lists to service_role;
grant select, insert, update, delete on public.list_members to service_role;
grant select, insert, update, delete on public.book_states to service_role;
