#!/bin/bash
set -e

# Docker named volumes mount as root:root, overriding any chown applied
# during the image build. Fix ownership at container start, before the app
# runs, then drop privileges permanently via gosu.
chown -R dsgUser:dsgUser /app/log /app/sqlite_db

# Migrate once, before any Robyn process starts, so worker processes never
# race each other on the schema.
gosu dsgUser alembic upgrade head

exec gosu dsgUser "$@"
