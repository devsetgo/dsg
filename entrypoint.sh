#!/bin/bash
set -e

# Docker named volumes mount as root:root, overriding any chown applied
# during the image build. Fix ownership here at container start, before
# the app process runs, then drop privileges permanently via gosu.
chown -R dsgUser:dsgUser /app/log

exec gosu dsgUser "$@"
