#!/bin/bash

# Pastikan direktori dimiliki oleh user yang benar
chown -R perwadaguser:perwadaguser /app/logs /app/static/uploads

# Set permission direktori (hanya perwadaguser bisa tulis)
chmod -R 755 /app/logs /app/static/uploads

# Jalankan command default
exec "$@"
