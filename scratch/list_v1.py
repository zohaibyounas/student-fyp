import requests
GEMINI_API_KEY = "AIzaSyD-56uwDnGk3SsMTqWjkx9p8TDwkKUfD_A"
url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
print(requests.get(url).text)
