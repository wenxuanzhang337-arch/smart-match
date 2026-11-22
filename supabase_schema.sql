-- Run this ONCE in Supabase:  SQL Editor -> New query -> paste -> Run.
-- Creates the table that stores anonymized respondents.
create table if not exists public.respondents (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  email       text not null,
  major       text,
  year        text,
  course      text,
  roles       jsonb default '[]'::jsonb,
  hours       text,
  meeting     jsonb default '[]'::jsonb,
  load        jsonb default '[]'::jsonb,
  grade       text,
  expect      text,
  discussion  text,
  decision    text,
  deadline    text,
  reliability text,
  stats       jsonb default '{}'::jsonb,
  created_at  timestamptz default now()
);

-- Allow the public (anon) key to read and insert, but not update/delete.
alter table public.respondents enable row level security;

create policy "anon_read" on public.respondents
  for select using (true);

create policy "anon_insert" on public.respondents
  for insert with check (true);

-- Tables created via raw SQL need this grant for the anon role to reach them.
grant select, insert on public.respondents to anon;
