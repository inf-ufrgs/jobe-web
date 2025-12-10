# This script assumes you are connected to the running jobe-server Kubernetes Service on localhost port 4000
# to achieve this you can use kubectl port-forward like so:
#   kubectl port-forward -n jobe-web svc/jobe-service 4000:80

import requests

# Using the forwarded port
JOBE_URL = "http://localhost:4000/jobe/index.php/restapi/languages"

try:
    print(f"Connecting to Jobe at {JOBE_URL}...")
    response = requests.get(JOBE_URL)
    
    if response.status_code == 200:
        languages = response.json()
        print("✅ Success! Jobe is running.")
        print(f"Supported Languages found: {len(languages)}")
        
        # List all supported languages
        for lang in languages:
            print(f" - {lang[0]} (Version: {lang[1]})")
    else:
        print(f"❌ Error: Server returned status code {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Connection Failed: {e}")