import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import the FastAPI app
from main import app

# Print all registered routes
print("\nRegistered routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"- {route.path}")
    elif hasattr(route, 'routes'):
        for r in route.routes:
            print(f"- {r.path}")

# Check if the health check endpoint is registered
health_endpoint = "/api/health"
health_registered = any(
    hasattr(route, 'path') and route.path == health_endpoint 
    or hasattr(route, 'routes') and any(r.path == health_endpoint for r in route.routes)
    for route in app.routes
)

status = "registered" if health_registered else "not registered"
print(f"\nHealth check endpoint {health_endpoint} is {status}")
