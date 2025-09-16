import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Create a simple FastAPI app for testing
app = FastAPI()

@app.get("/test")
async def test_endpoint():
    return {"message": "Test endpoint is working!"}

# Create a test client
client = TestClient(app)

# Test the test endpoint
def test_test_endpoint():
    response = client.get("/test")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

if __name__ == "__main__":
    print("Testing simple FastAPI application...")
    if test_test_endpoint():
        print("✅ Simple test passed!")
    else:
        print("❌ Simple test failed!")
