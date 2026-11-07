-- Remote access was unavailable. Inspect the existing schema before running.
-- Idempotent bootstrap for a dedicated, server-only demo document store.
begin;
create schema if not exists "aio-03-p2-team1-demo";
create table if not exists "aio-03-p2-team1-demo".documents (
  owner text not null,
  kind text not null check (kind in ('identity','thread','memory','saved','run','subscription','notification')),
  id text not null,
  data jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (owner, kind, id)
);
create index if not exists documents_owner_kind_updated on "aio-03-p2-team1-demo".documents (owner, kind, updated_at desc);
alter table "aio-03-p2-team1-demo".documents enable row level security;
revoke all on "aio-03-p2-team1-demo".documents from anon, authenticated;
grant usage on schema "aio-03-p2-team1-demo" to service_role;
grant select, insert, update, delete on "aio-03-p2-team1-demo".documents to service_role;
-- No anon/authenticated policies: API server checks hashed demo-token ownership.
commit;
