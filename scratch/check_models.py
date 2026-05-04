import requests
import os

GEMINI_API_KEY = "AIzaSyDqy1EP6HLXi5JZXX9j7Ohth0TKdTva2-I"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        models = response.json().get('models', [])
        print("Available models:")
        for model in models:
            print(f" - {model['name']}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
