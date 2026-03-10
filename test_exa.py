import os
import asyncio
from exa_py import Exa

# Load environment variables manually
EXA_KEY = None
with open(".env") as f:
    for line in f:
        if line.startswith("EXA_API_KEY="):
            EXA_KEY = line.strip().split("=", 1)[1].strip("\'\"")

if not EXA_KEY:
    print("No EXA_API_KEY found in .env")
    exit(1)

exa_client = Exa(EXA_KEY)

query = "pizza promotions food delivery detroit 2025"
start_str = "2025-06-01"
end_str = "2025-06-20"

print(f"Executing Exa Search:\nQuery: {query}\nStart: {start_str}\nEnd: {end_str}\n")

try:
    response = exa_client.search_and_contents(
        query,
        num_results=5,
        start_published_date=start_str,
        end_published_date=end_str
    )
    
    print(f"Results Found: {len(response.results)}\n")
    for idx, res in enumerate(response.results):
        print(f"--- Result {idx + 1} ---")
        print(f"Title: {res.title}")
        print(f"URL: {res.url}")
        print(f"Date: {res.published_date}")
        snippet = res.text[:200].replace('\n', ' ') if res.text else "No text"
        print(f"Snippet: {snippet}...\n")
        
except Exception as e:
    print(f"Exa search failed: {str(e)}")
