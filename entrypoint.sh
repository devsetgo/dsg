#!/bin/bash
set -e

# Docker named volumes mount as root:root, overriding any chown applied
# during the image build. Fix ownership here at container start, before
# the app process runs, then drop privileges permanently via gosu.
chown -R dsgUser:dsgUser /app/log

# Run migrations once, synchronously, before any uvicorn worker starts.
# This avoids the async/sync deadlock that occurs when multiple workers
# race to call alembic inside an already-running asyncpg event loop.
gosu dsgUser alembic upgrade head

exec gosu dsgUser "$@"
