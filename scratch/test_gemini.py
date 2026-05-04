import requests

GEMINI_API_KEY = "AIzaSyDqy1EP6HLXi5JZXX9j7Ohth0TKdTva2-I"
model_name = "gemini-1.5-flash-latest"
url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

try:
    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": "Hello"}]}]},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
