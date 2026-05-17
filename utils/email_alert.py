import smtplib
from email.message import EmailMessage

from config import EMAIL_CONFIG, email_is_configured


def _build_mental_health_body(user_name, negative_count):
    return f"""Assalamu Alaikum {user_name},

⚠️  MENTAL HEALTH ALERT — Islamic Dream Analyzer

Aap ne is hafte {negative_count} negative dreams record kiye hain.
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
"""


def send_mental_health_email(to_email, user_name="User", negative_count=7):
    """
    Send mental health alert email.
    Returns dict: success, email_sent, message, error (optional).
    Never raises — caller always gets JSON-safe result.
    """
    if not email_is_configured():
        return {
            "success": True,
            "email_sent": False,
            "message": "Alert recorded! (Email server configured nahi hai abhi)",
            "error": (
                "Set EMAIL_SENDER and EMAIL_PASSWORD in .env — use a Gmail App Password, "
                "not your normal Gmail password. Google Account → Security → App Passwords."
            ),
        }

    msg = EmailMessage()
    msg["Subject"] = "🌙 Islamic Dream Analyzer — Mental Health Alert"
    msg["From"] = EMAIL_CONFIG["sender"]
    msg["To"] = to_email
    msg.set_content(_build_mental_health_body(user_name, negative_count))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(EMAIL_CONFIG["sender"], EMAIL_CONFIG["password"])
            server.send_message(msg)
        return {
            "success": True,
            "email_sent": True,
            "message": "Mental health alert email bhej diya gaya!",
        }
    except smtplib.SMTPAuthenticationError:
        return {
            "success": True,
            "email_sent": False,
            "message": "Alert recorded! (Gmail login fail — App Password chahiye)",
            "error": (
                "Gmail ne password reject kiya. Regular password kaam nahi karta — "
                "Google Account → Security → 2-Step Verification → App Passwords se "
                "16-character App Password banao aur .env mein EMAIL_PASSWORD set karo."
            ),
        }
    except smtplib.SMTPException as e:
        return {
            "success": True,
            "email_sent": False,
            "message": "Alert recorded! (Email server error)",
            "error": str(e),
        }
    except OSError as e:
        return {
            "success": True,
            "email_sent": False,
            "message": "Alert recorded! (Network / SMTP connection error)",
            "error": str(e),
        }


def send_alert(to_email, negative_count):
    """Simple tracker alert (legacy helper)."""
    return send_mental_health_email(to_email, user_name="User", negative_count=negative_count)
