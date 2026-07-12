alter table public.books
    add column openlibrary_cover_id integer;

alter table public.book_states
    add column wanted boolean not null default true;
