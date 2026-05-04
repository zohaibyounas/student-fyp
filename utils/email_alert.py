import smtplib
from email.message import EmailMessage
from config import EMAIL_CONFIG

def send_alert(to_email, negative_count):
    msg = EmailMessage()
    msg["Subject"] = "⚠️ Dream Tracker Alert"
    msg["From"] = EMAIL_CONFIG["sender"]
    msg["To"] = to_email

    msg.set_content(
        f"""
        Alert!

        You have recorded {negative_count} negative dreams.
        This may indicate stress or emotional imbalance.

        Islamic Advice:
        Increase remembrance of Allah and recite Ayat-ul-Kursi before sleep.
        """
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            EMAIL_CONFIG["sender"],
            EMAIL_CONFIG["password"]
        )
        server.send_message(msg)
