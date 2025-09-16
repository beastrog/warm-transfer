import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from main import app

print("Registered routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"- {route.path}")
    elif hasattr(route, 'routes'):
        for r in route.routes:
            print(f"- {r.path}")
