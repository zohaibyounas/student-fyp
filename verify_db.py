import os
os.environ['DATABASE_URL'] = 'postgresql://islamic_dream_db_user:cWM5ytIu8WIQiKDCk6jgHGI6CY5B6Yle@dpg-d7seo1t0lvsc73fnnlg0-a.singapore-postgres.render.com/islamic_dream_db'

# Now import and test the config
from config import conn

if conn:
    print("✅ Database connected successfully!")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM dreams")
            count = cursor.fetchone()[0]
            print(f"📊 Dreams in database: {count}")
        conn.close()
    except Exception as e:
        print(f"❌ Database query error: {e}")
else:
    print("❌ Database not connected")