# config.py — Database configuration for PostgreSQL (Render)
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

# Try to connect — but don't crash if DB is unavailable
conn = None
if DATABASE_URL:
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"⚠️  Database not connected (app will still work without it): {e}")
else:
    print("⚠️  DATABASE_URL not set (app will still work without it)")
