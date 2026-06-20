create extension if not exists vector with schema extensions;

-- subjects: a grouping of related sources; the unit of retrieval scope.
create table public.subjects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now()
);

create table public.sources (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references public.subjects (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  filename text not null,
  content_hash text not null,
  storage_path text not null,
  created_at timestamptz not null default now()
);

-- chunks: retrieval units. embedding is a pgvector column
create table public.chunks (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources (id) on delete cascade,
  subject_id uuid not null references public.subjects (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  content text not null,
  embedding vector(384)
);

create table public.concepts (
  id uuid primary key default gen_random_uuid(),
  subject_id uuid not null references public.subjects (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  rubric jsonb not null default '{}'::jsonb,
  source_hash text
);

create table public.mastery (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  concept_id uuid not null references public.concepts (id) on delete cascade,
  ease real not null default 2.5,
  interval integer not null default 0,
  next_review timestamptz,
  comprehension integer not null default 0,
  updated_at timestamptz not null default now(),
  -- one mastery row per user per concept; drives SRS and the student's growth.
  unique (user_id, concept_id)
);

create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  concept_id uuid not null references public.concepts (id) on delete cascade,
  status text not null default 'in_progress' check (status in ('in_progress', 'completed')),
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  transcript jsonb not null default '[]'::jsonb,
  results jsonb
);

create index on public.sources (subject_id);
create index on public.chunks (subject_id);  -- retrieval is always subject-scoped
create index on public.chunks (source_id);
create index on public.concepts (subject_id);
create index on public.mastery (user_id, next_review);  -- "due for review" dashboard query
create index on public.sessions (user_id, status);  -- offer in-progress sessions to resume

-- Row Level Security: a row is readable and writable only by its owner.
-- `using` gates reads/updates/deletes; `with check` stops a user writing a row
-- stamped with someone else's user_id. Scoped to the authenticated role so
-- anonymous requests (auth.uid() is null) match nothing.
alter table public.subjects enable row level security;
alter table public.sources enable row level security;
alter table public.chunks enable row level security;
alter table public.concepts enable row level security;
alter table public.mastery enable row level security;
alter table public.sessions enable row level security;

create policy subjects_owner on public.subjects for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy sources_owner on public.sources for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy chunks_owner on public.chunks for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy concepts_owner on public.concepts for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy mastery_owner on public.mastery for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy sessions_owner on public.sessions for all to authenticated
  using (user_id = auth.uid()) with check (user_id = auth.uid());
