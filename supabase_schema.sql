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

-- Comments / feedback (for the sidebar "Feedback" section).
create table if not exists public.comments (
  id          uuid primary key default gen_random_uuid(),
  author      text,
  body        text not null,
  created_at  timestamptz default now()
);
alter table public.comments enable row level security;
create policy "anon_read_comments" on public.comments for select using (true);
create policy "anon_insert_comments" on public.comments for insert with check (true);
grant select, insert on public.comments to anon;

-- Reports (举报) + praise (好评) for the sidebar "Report" section.
create table if not exists public.reports (
  id          uuid primary key default gen_random_uuid(),
  target_name text not null,
  label       text not null,
  evidence    text,
  verdict     text default 'pending',
  created_at  timestamptz default now()
);
alter table public.reports enable row level security;
create policy "anon_read_reports" on public.reports for select using (true);
create policy "anon_insert_reports" on public.reports for insert with check (true);
grant select, insert on public.reports to anon;

create table if not exists public.praise (
  id          uuid primary key default gen_random_uuid(),
  target_name text not null,
  created_at  timestamptz default now()
);
alter table public.praise enable row level security;
create policy "anon_read_praise" on public.praise for select using (true);
create policy "anon_insert_praise" on public.praise for insert with check (true);
grant select, insert on public.praise to anon;
