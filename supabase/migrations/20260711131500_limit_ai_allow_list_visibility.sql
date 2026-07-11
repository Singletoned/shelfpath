drop policy if exists "allowed users can read their allow-list row" on public.ai_series_suggestion_allowed_users;

create policy "allowed users can read their own allow-list row"
    on public.ai_series_suggestion_allowed_users for select
    to authenticated
    using (
        user_id = auth.uid()
        or lower(email) = lower((auth.jwt() ->> 'email'))
    );
