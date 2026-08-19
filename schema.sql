create extension if not exists pgcrypto;
create extension if not exists pg_cron;

create table if not exists public.shops (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  upi_id text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.print_jobs (
  id bigserial primary key,
  shop_id uuid not null references public.shops(id) on delete cascade,
  file_path text not null,
  original_file_name text not null,
  page_count integer not null check (page_count > 0),
  sheet_count integer not null check (sheet_count > 0),
  copy_count integer not null check (copy_count > 0),
  color_mode text not null check (color_mode in ('bw', 'color')),
  duplex_mode text not null check (duplex_mode in ('single', 'double')),
  total_amount numeric(10,2) not null check (total_amount >= 0),
  payment_status text not null default 'pending' check (payment_status in ('pending', 'paid', 'failed')),
  print_status text not null default 'queued' check (print_status in ('queued', 'printing', 'completed', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists print_jobs_lookup_idx
  on public.print_jobs (shop_id, payment_status, print_status, created_at);

alter table public.shops enable row level security;
alter table public.print_jobs enable row level security;

drop policy if exists "public can read shops" on public.shops;
create policy "public can read shops"
  on public.shops for select
  using (true);

drop policy if exists "public can create print jobs" on public.print_jobs;
create policy "public can create print jobs"
  on public.print_jobs for insert
  with check (true);

drop policy if exists "public can read print jobs" on public.print_jobs;
create policy "public can read print jobs"
  on public.print_jobs for select
  using (true);

drop policy if exists "public can update print jobs" on public.print_jobs;
create policy "public can update print jobs"
  on public.print_jobs for update
  using (true)
  with check (true);

do $$
begin
  begin
    alter publication supabase_realtime add table public.print_jobs;
  exception
    when duplicate_object then null;
  end;
end $$;

create or replace function public.cleanup_old_print_jobs()
returns void
language plpgsql
as $$
begin
  delete from public.print_jobs
  where created_at < now() - interval '30 minutes';
end;
$$;

select cron.unschedule('cleanup_old_print_jobs_30m')
where exists (
  select 1 from cron.job where jobname = 'cleanup_old_print_jobs_30m'
);

select cron.schedule(
  'cleanup_old_print_jobs_30m',
  '*/30 * * * *',
  $$select public.cleanup_old_print_jobs();$$
);
