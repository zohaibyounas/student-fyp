import os
import psycopg2

# Set DATABASE_URL (replace with your actual URL)
DATABASE_URL = "postgresql://islamic_dream_db_user:cWM5ytIu8WIQiKDCk6jgHGI6CY5B6Yle@dpg-d7seo1t0lvsc73fnnlg0-a.singapore-postgres.render.com/islamic_dream_db"

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Database connected successfully!")

    # Create table
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dreams (
                id SERIAL PRIMARY KEY,
                dream_text TEXT NOT NULL,
                sentiment TEXT,
                islamic TEXT,
                meaning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    print("✅ Dreams table created successfully!")

    # Test insert
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO dreams (dream_text, sentiment, islamic, meaning) VALUES (%s, %s, %s, %s)",
            ("Test dream", "positive", "rehmani", "Test meaning")
        )
        conn.commit()
    print("✅ Test data inserted successfully!")

    # Test select
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM dreams")
        count = cursor.fetchone()[0]
    print(f"✅ Table has {count} records")

    conn.close()
    print("✅ Database connection test completed!")

except Exception as e:
    print(f"❌ Error: {e}")