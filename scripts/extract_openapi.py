import json
import os
import sys

# Add the backend directory to the Python path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from app.main import app

def generate_openapi():
    # Force FastAPI to generate the OpenAPI schema
    openapi_schema = app.openapi()
    
    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docs'))
    os.makedirs(docs_dir, exist_ok=True)
    
    output_path = os.path.join(docs_dir, 'openapi.json')
    
    with open(output_path, 'w') as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f"✅ Successfully wrote OpenAPI schema to {output_path}")

if __name__ == "__main__":
    generate_openapi()
