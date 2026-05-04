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
        print("🔌 Database connection established")
        
        with conn.cursor() as cursor:
            print("🏗️  Creating tables...")
            
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
            print("✅ Users table created/verified")
            
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
            print("✅ User dreams table created/verified")
            
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
            print("✅ Dreams table created/verified")
            
            conn.commit()
            print("✅ All tables committed successfully")
        
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection/setup error: {e}")
        conn = None
else:
    print("⚠️  DATABASE_URL not set (app will still work without it)")
