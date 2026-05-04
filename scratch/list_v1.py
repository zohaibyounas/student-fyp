import requests
GEMINI_API_KEY = "AIzaSyDqy1EP6HLXi5JZXX9j7Ohth0TKdTva2-I"
url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
print(requests.get(url).text)
