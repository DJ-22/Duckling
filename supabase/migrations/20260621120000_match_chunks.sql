-- Scoped similarity search over chunks. SECURITY INVOKER so the caller's RLS
-- policy applies: a user can only ever match their own rows, and the subject
-- filter narrows the search to one subject's material (the retrieval scope).
create or replace function public.match_chunks(
  query_embedding extensions.vector(384),
  match_subject_id uuid,
  match_count integer default 5
)
returns table (id uuid, content text, distance double precision)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  select c.id, c.content, (c.embedding <=> query_embedding) as distance
  from public.chunks c
  where c.subject_id = match_subject_id
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

revoke all on function public.match_chunks(extensions.vector, uuid, integer) from public;
grant execute on function public.match_chunks(extensions.vector, uuid, integer) to authenticated;
