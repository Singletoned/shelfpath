create or replace function public.local_auth_user_by_email(target_email text)
returns uuid
language sql
security definer
set search_path = public, auth
stable
as $$
    select users.id
    from auth.users users
    where lower(users.email) = lower(target_email)
    limit 1;
$$;

revoke all on function public.local_auth_user_by_email(text) from public;
grant execute on function public.local_auth_user_by_email(text) to service_role;
