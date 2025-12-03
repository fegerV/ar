import requests
import os

# Test creating an order
url = "http://localhost:8000/orders/create"

# We'll need to provide image and video files for the test
# For now, let's just check if the endpoint is accessible
try:
    response = requests.get(url)
    print(f"GET {url}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Also test the admin panel
try:
    response = requests.get("http://localhost:8000/admin")
    print(f"\nGET http://localhost:8000/admin")
    print(f"Status Code: {response.status_code}")
    print(f"Response length: {len(response.text)} characters")
except Exception as e:
    print(f"Error: {e}")
