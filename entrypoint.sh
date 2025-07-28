#!/bin/bash
set -e

# Fix permissions for mounted volumes as root
chown -R perwadaguser:perwadaguser /app/static/uploads /app/logs 2>/dev/null || true
chmod -R 755 /app/static/uploads /app/logs 2>/dev/null || true

# Remove any existing log files that might have wrong permissions
rm -f /app/logs/*.log 2>/dev/null || true

# Switch to perwadaguser and execute command
exec gosu perwadaguser "$@"
