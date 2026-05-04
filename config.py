# config.py — Database configuration for PostgreSQL (Render)
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

# Try to connect — but don't crash if DB is unavailable
conn = None
if DATABASE_URL:
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_dreams (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    dream_text TEXT NOT NULL,
                    sentiment TEXT,
                    islamic TEXT,
                    meaning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS dreams (
                    id SERIAL PRIMARY KEY,
                    dream_text TEXT NOT NULL,
                    sentiment TEXT,
                    islamic TEXT,
                    meaning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"⚠️  Database not connected (app will still work without it): {e}")
        conn = None
else:
    print("⚠️  DATABASE_URL not set (app will still work without it)")
