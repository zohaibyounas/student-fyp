from flask import Flask, request, jsonify, render_template
import pickle
import re
import os
import requests
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from config import conn

app = Flask(__name__)

# ─── Text Cleaner ────────────────────────────────────────────────────────────
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# ─── Load ML Models ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    sentiment_model = pickle.load(open(os.path.join(BASE_DIR, "models/sentiment_model.pkl"), "rb"))
    print("✅ Sentiment model loaded")
except Exception as e:
    print(f"⚠️  Could not load sentiment model: {e}")
    sentiment_model = None

try:
    islamic_model = pickle.load(open(os.path.join(BASE_DIR, "models/islamic_model.pkl"), "rb"))
    print("✅ Islamic model loaded")
except Exception as e:
    print(f"⚠️  Could not load Islamic model: {e}")
    islamic_model = None

if conn:
    print("✅ Database connected successfully")
else:
    print("⚠️  Database not connected (app will work without it)")

# ─── Helper Functions ─────────────────────────────────────────────────────────
def get_user_by_email(email):
    if not conn:
        return None
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s", (email,))
        return cursor.fetchone()

# ─── Dream Analyzer ──────────────────────────────────────────────────────────
def analyze_dream_ml(text):
    clean = clean_text(text)
    if sentiment_model:
        sentiment = sentiment_model.predict([clean])[0]
    else:
        sentiment = "neutral"
    if islamic_model:
        islamic = islamic_model.predict([clean])[0]
    else:
        islamic = "nafsani"
    meaning = f"This dream reflects {sentiment} emotions and {islamic} influence."
    return sentiment, islamic, meaning

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("Islamic Dream Analyzer.html")

@app.route("/test", methods=["GET"])
def test():
    db_status = "connected" if conn else "not connected"
    db_count = 0
    users_count = 0
    user_dreams_count = 0
    tables_info = {}
    
    if conn:
        try:
            with conn.cursor() as cursor:
                # Check what tables exist
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cursor.fetchall()
                tables_info["existing_tables"] = [table[0] for table in tables]
                
                # Try to count from each table
                if "dreams" in tables_info["existing_tables"]:
                    cursor.execute("SELECT COUNT(*) FROM dreams")
                    db_count = cursor.fetchone()[0]
                
                if "users" in tables_info["existing_tables"]:
                    cursor.execute("SELECT COUNT(*) FROM users")
                    users_count = cursor.fetchone()[0]
                else:
                    tables_info["users_table_missing"] = True
                
                if "user_dreams" in tables_info["existing_tables"]:
                    cursor.execute("SELECT COUNT(*) FROM user_dreams")
                    user_dreams_count = cursor.fetchone()[0]
                else:
                    tables_info["user_dreams_table_missing"] = True
                    
        except Exception as e:
            db_status = f"error: {str(e)}"
            tables_info["error"] = str(e)
    
    return jsonify({
        "status": "ok", 
        "message": "Server is running",
        "database": {
            "status": db_status,
            "dreams_count": db_count,
            "users_count": users_count,
            "user_dreams_count": user_dreams_count,
            **tables_info
        },
        "models": {
            "sentiment": "loaded" if sentiment_model else "not loaded",
            "islamic": "loaded" if islamic_model else "not loaded"
        }
    })

@app.route("/api/register", methods=["POST"])
def register():
    print(f"🔍 Registration attempt received")
    if not conn:
        print("❌ Database not connected")
        return jsonify({"error": "Database not connected"}), 500
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    print(f"📝 Registration data: name={name}, email={email}, password_length={len(password)}")
    
    if not name or not email or not password:
        print("❌ Missing required fields")
        return jsonify({"error": "Name, email, and password are required"}), 400
    if len(password) < 6:
        print("❌ Password too short")
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    try:
        existing_user = get_user_by_email(email)
        print(f"🔍 Existing user check: {existing_user}")
        if existing_user:
            print("❌ Email already registered")
            return jsonify({"error": "Email already registered"}), 400
        
        password_hash = generate_password_hash(password)
        print("🔐 Password hashed successfully")
        
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name, email",
                (name, email, password_hash)
            )
            user = cursor.fetchone()
            conn.commit()
            print(f"✅ User inserted successfully: {user}")
        return jsonify({"user": {"id": user[0], "name": user[1], "email": user[2]}})
    except Exception as e:
        print(f"❌ Registration error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def login():
    print(f"🔍 Login attempt received")
    if not conn:
        print("❌ Database not connected")
        return jsonify({"error": "Database not connected"}), 500
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    print(f"📝 Login data: email={email}, password_length={len(password)}")
    
    if not email or not password:
        print("❌ Missing email or password")
        return jsonify({"error": "Email and password are required"}), 400
    try:
        user = get_user_by_email(email)
        print(f"🔍 User lookup result: {user}")
        if not user:
            print("❌ User not found")
            return jsonify({"error": "Invalid credentials"}), 401
        user_id, user_name, user_email, password_hash = user
        password_valid = check_password_hash(password_hash, password)
        print(f"🔐 Password check: {'valid' if password_valid else 'invalid'}")
        if not password_valid:
            print("❌ Invalid password")
            return jsonify({"error": "Invalid credentials"}), 401
        print(f"✅ Login successful for user: {user_name}")
        return jsonify({"user": {"id": user_id, "name": user_name, "email": user_email}})
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/user-dreams", methods=["GET", "POST"])
def user_dreams():
    if not conn:
        return jsonify({"error": "Database not connected"}), 500
    if request.method == "GET":
        email = request.args.get("email", "").strip().lower()
        if not email:
            return jsonify({"error": "Email is required"}), 400
        user = get_user_by_email(email)
        if not user:
            return jsonify({"error": "User not found"}), 404
        user_id = user[0]
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, dream_text, sentiment, islamic, meaning, created_at FROM user_dreams WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                rows = cursor.fetchall()
            dreams = [
                {
                    "id": row[0],
                    "dream_text": row[1],
                    "sentiment": row[2],
                    "islamic": row[3],
                    "meaning": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in rows
            ]
            return jsonify({"dreams": dreams})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        data = request.json or {}
        email = data.get("email", "").strip().lower()
        dream_text = data.get("dream_text", "").strip()
        sentiment = data.get("sentiment", "")
        islamic = data.get("islamic", "")
        meaning = data.get("meaning", "")
        dream_id = data.get("id")
        if not email or not dream_text:
            return jsonify({"error": "Email and dream text are required"}), 400
        user = get_user_by_email(email)
        if not user:
            return jsonify({"error": "User not found"}), 404
        user_id = user[0]
        try:
            with conn.cursor() as cursor:
                if dream_id:
                    cursor.execute(
                        "UPDATE user_dreams SET dream_text=%s, sentiment=%s, islamic=%s, meaning=%s WHERE id=%s AND user_id=%s RETURNING id, created_at",
                        (dream_text, sentiment, islamic, meaning, dream_id, user_id)
                    )
                    updated = cursor.fetchone()
                    if not updated:
                        return jsonify({"error": "Dream not found or not owned by user"}), 404
                    conn.commit()
                    result_id, created_at = updated
                else:
                    cursor.execute(
                        "INSERT INTO user_dreams (user_id, dream_text, sentiment, islamic, meaning) VALUES (%s, %s, %s, %s, %s) RETURNING id, created_at",
                        (user_id, dream_text, sentiment, islamic, meaning)
                    )
                    result_id, created_at = cursor.fetchone()
                    conn.commit()
            return jsonify({
                "dream": {
                    "id": result_id,
                    "dream_text": dream_text,
                    "sentiment": sentiment,
                    "islamic": islamic,
                    "meaning": meaning,
                    "created_at": created_at.isoformat() if created_at else None
                }
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/user-dreams/<int:dream_id>", methods=["DELETE"])
def delete_user_dream(dream_id):
    if not conn:
        return jsonify({"error": "Database not connected"}), 500
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400
    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_id = user[0]
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_dreams WHERE id = %s AND user_id = %s RETURNING id",
                (dream_id, user_id)
            )
            deleted = cursor.fetchone()
            if not deleted:
                return jsonify({"error": "Dream not found or not owned by user"}), 404
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/analyze-dream", methods=["POST"])
def dream_analyzer():
    data = request.json
    dream_text = data.get("dream_text", "").strip()
    if not dream_text:
        return jsonify({"error": "Dream text is required"}), 400
    try:
        sentiment, islamic, meaning = analyze_dream_ml(dream_text)
        
        # Save to database if connected
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO dreams (dream_text, sentiment, islamic, meaning) VALUES (%s, %s, %s, %s)",
                        (dream_text, sentiment, islamic, meaning)
                    )
                    conn.commit()
                print("✅ Dream saved to database")
            except Exception as db_e:
                print(f"⚠️  Could not save to database: {db_e}")
        
        return jsonify({"sentiment": sentiment, "islamic_analysis": islamic, "meaning": meaning})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── AI Chatbot (Gemini API) ──────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDqy1EP6HLXi5JZXX9j7Ohth0TKdTva2-I")

@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.json
    user_message = data.get("message", "").strip()
    history = data.get("history", [])

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    if GEMINI_API_KEY == "I was in deep water and struggling to stay above the surface" or not GEMINI_API_KEY:
        return jsonify({
            "error": " GEMINI_API_KEY not working "
        }), 503

    SYSTEM_PROMPT = (
        "You are DreamBot, an expert Islamic dream interpreter and emotional support assistant.\n\n"
        "Rules:\n"
        "- Only provide meanings based on authentic Islamic sources (Quran, Hadith, Ibn Sirin, Al-Nabulsi).\n"
        "- Do NOT fabricate references. If no authentic reference is known, say 'No authentic reference found'.\n"
        "- For every dream interpretation, provide:\n"
        "  1. Meaning (detailed)\n"
        "  2. Category: Positive / Neutral / Negative\n"
        "  3. Type: Rehmani (from Allah) / Shaitani (from Shaytan) / Nafsani (from self)\n"
        "  4. Reference (Hadith / Scholar name)\n"
        "  5. Brief explanation in simple Urdu at the end (labeled 'اردو تشریح:')\n\n"
        "Format dream analysis with clear sections using emojis:\n"
        "🔮 **Dream Meaning:** ...\n"
        "📊 **Category:** ...\n"
        "✨ **Type:** ...\n"
        "📚 **Reference:** ...\n"
        "🕌 **اردو تشریح:** ...\n\n"
        "For non-dream emotional support messages, respond warmly and Islamically.\n"
        "Always be empathetic, supportive, and spiritually grounded."
    )

    gemini_contents = [
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
        {"role": "model", "parts": [{"text": "Understood. I am DreamBot, ready to interpret Islamic dreams. Assalamu Alaikum!"}]}
    ]
    for h in history[-10:]:
        role = "user" if h["role"] == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": h["content"]}]})
    gemini_contents.append({"role": "user", "parts": [{"text": user_message}]})

    try:
        # Using gemini-1.5-flash which is the current stable flash model
        model_name = "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": gemini_contents, "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7}},
            timeout=30
        )
        
        if response.status_code == 404:
            return jsonify({"error": f"Gemini Model '{model_name}' not found. Please check if the model name is correct or available in your region."}), 503
            
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            err_msg = result["error"].get("message", "Unknown error")
            return jsonify({"error": f"Gemini error: {err_msg}"}), 503

        if not result.get("candidates"):
            return jsonify({"error": "Gemini gave empty response. This usually means the safety filters blocked the content or the API key is restricted."}), 503

        bot_reply = result["candidates"][0]["content"]["parts"][0]["text"]
        return jsonify({"reply": bot_reply})

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else 0
        if status == 403:
            return jsonify({"error": "Gemini API key is blocked or invalid (possibly reported as leaked). Please get a new key from: https://aistudio.google.com/app/apikey and set it as GEMINI_API_KEY environment variable."}), 503
        elif status == 400:
            return jsonify({"error": f"Bad Request to Gemini API. Details: {e.response.text}"}), 503
        elif status == 429:
            return jsonify({"error": "API rate limit exceeded. Please wait a moment and try again."}), 503
        return jsonify({"error": f"Gemini HTTP error {status}: {str(e)}"}), 503
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Internet connection check . Gemini API is not connecting ."}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Gemini API timeout .  try again."}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Mental Health Email Alert ────────────────────────────────────────────────
# 👇 APNI GMAIL AUR APP PASSWORD YAHAN DAALO
# Gmail App Password kaise banayein: Google Account > Security > 2-Step Verification > App Passwords
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER",   "fataekim2601@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "kim2601@")

@app.route("/send-mental-health-alert", methods=["POST"])
def send_mental_health_alert():
    data           = request.json
    to_email       = data.get("email", "").strip()
    negative_count = data.get("negativeCount", 7)
    user_name      = data.get("userName", "User")

    if not to_email:
        return jsonify({"error": "Email address required hai"}), 400

    # If email not configured, still return success (app works, just no email)
    if EMAIL_SENDER == "fataekim2601@gmail.com" or EMAIL_PASSWORD == "kim2601@":
        print(f"⚠️  Email not configured — would have sent alert to {to_email}")
        return jsonify({
            "success": True,
            "message": "Alert recorded! (Email server configured nahi hai abhi)",
            "email_sent": False
        })

    try:
        msg            = EmailMessage()
        msg["Subject"] = "🌙 Islamic Dream Analyzer — Mental Health Alert"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = to_email
        msg.set_content(f"""Assalamu Alaikum {user_name},

⚠️  MENTAL HEALTH ALERT — Islamic Dream Analyzer

Aap ne {negative_count} consecutive negative dreams record kiye hain.
Yeh pattern stress, anxiety, ya emotional imbalance ki nishani ho sakta hai.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Islamic Guidance & Suggestions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 📿 Sone se pehle Ayat-ul-Kursi (2:255) parhein
2. 🌙 Sone se pehle Surah Ikhlas, Falaq, Naas teen teen baar parhein
3. 🤲 Dua: "A'oothu bi kalimaatillaahit-taammaati min sharri maa khalaq"
4. 💚 Kisi trusted Islamic counselor ya mental health professional se baat karein
5. 🧘 Din mein dhikr ki practice karein — SubhanAllah, Alhamdulillah, Allahu Akbar
6. 😴 Raat ko 7-8 ghante ki neend zaroor lein

Rasool Allah ﷺ ne farmaya: "Agar koi bura khwab dekhe to Shaytan se Allah ki panaah maange aur us khwab ki burai se bhi." (Bukhari & Muslim)

Aap akele nahi hain. Allah aapko sukoon aur sehat ata farmaye. Ameen.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Islamic Dream Analyzer — Mental Health Support
""")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"✅ Mental health alert sent to {to_email}")
        return jsonify({"success": True, "message": "Mental health alert email bhej diya gaya!", "email_sent": True})

    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "error": "Gmail login fail. Regular password nahi, App Password use karo.",
            "help": "Google Account > Security > 2-Step Verification > App Passwords"
        }), 500
    except Exception as e:
        return jsonify({"error": f"Email send nahi hua: {str(e)}"}), 500


# ─── Dream Diary ──────────────────────────────────────────────────────────────
@app.route("/api/dreams", methods=["GET"])
def get_dreams():
    if not conn:
        return jsonify({"message": "Database not connected", "dreams": []})
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, dream_text, sentiment, islamic, meaning, created_at FROM dreams ORDER BY created_at DESC")
            rows = cursor.fetchall()
            dreams = [
                {
                    "id": row[0],
                    "dream_text": row[1],
                    "sentiment": row[2],
                    "islamic": row[3],
                    "meaning": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in rows
            ]
        return jsonify({"dreams": dreams})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/dreams", methods=["GET"])
def view_dreams():
    if not conn:
        return "Database not connected", 500
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT ud.id, u.email, ud.dream_text, ud.sentiment, ud.islamic, ud.meaning, ud.created_at "
                "FROM user_dreams ud "
                "JOIN users u ON ud.user_id = u.id "
                "ORDER BY ud.created_at DESC"
            )
            rows = cursor.fetchall()
        return render_template("dreams.html", dreams=rows)
    except Exception as e:
        return f"Error loading dreams: {str(e)}", 500

@app.route("/admin/db-viewer")
def db_viewer():
    if not conn:
        return "Database not connected", 500
    
    try:
        users = []
        user_dreams = []
        
        with conn.cursor() as cursor:
            # Get all users
            cursor.execute("SELECT id, name, email, created_at FROM users ORDER BY created_at DESC")
            user_rows = cursor.fetchall()
            users = [{"id": row[0], "name": row[1], "email": row[2], "created_at": row[3]} for row in user_rows]
            
            # Get all user dreams with user email
            cursor.execute("""
                SELECT ud.id, u.email, ud.dream_text, ud.sentiment, ud.islamic, ud.meaning, ud.created_at 
                FROM user_dreams ud 
                JOIN users u ON ud.user_id = u.id 
                ORDER BY ud.created_at DESC
            """)
            dream_rows = cursor.fetchall()
            user_dreams = [{
                "id": row[0], 
                "user_email": row[1], 
                "dream_text": row[2], 
                "sentiment": row[3], 
                "islamic": row[4], 
                "meaning": row[5], 
                "created_at": row[6]
            } for row in dream_rows]
            
    except Exception as e:
        return f"Database error: {str(e)}", 500
    
    return render_template("db_viewer.html", users=users, user_dreams=user_dreams)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
