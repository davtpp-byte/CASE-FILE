#!/bin/sh
# Prepare the persistent data directory and drop privileges for the app.
set -eu

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/data
    # A freshly attached Render disk is typically owned by root. Only do the
    # recursive fix once; a marker file keeps restarts cheap on large disks.
    if [ ! -f /app/data/.casefile-owned ]; then
        chown -R studio:studio /app/data 2>/dev/null || true
        touch /app/data/.casefile-owned
    else
        chown studio:studio /app/data 2>/dev/null || true
    fi
    exec gosu studio "$@"
fi

exec "$@"
