#!/usr/bin/with-contenv bashio
bashio::log.info "Starting Announcement Maker..."
exec python3 /app/server.py
