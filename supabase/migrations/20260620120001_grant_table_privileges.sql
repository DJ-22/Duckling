grant usage on schema public to authenticated, service_role;

grant select, insert, update, delete on all tables in schema public
  to authenticated, service_role;

-- So tables added by future migrations inherit the same grants automatically.
alter default privileges in schema public
  grant select, insert, update, delete on tables to authenticated, service_role;
