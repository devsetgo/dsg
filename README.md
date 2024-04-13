# www
Hugo site for DevSetGo.com and other static sites.

Feel free to fork the project, but the content is mine. Using Calver of YY.MM.DD






## Development SQL Scripts


Drop all tables for POSTGRES
```sql
DO $$ DECLARE
    r RECORD;
BEGIN
    -- if the schema you operate on is not "current", you will want to
    -- replace current_schema() in query with 'schematodeletetablesfrom'
    -- *and* update the generate 'DROP...' accordingly.
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        RAISE NOTICE 'Dropping table: %', r.tablename;
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;
```
