import requests
import json

r = requests.get('http://localhost:5000/api/sailors-for-onwater')
data = r.json()

print("Raw JSON response:")
print(json.dumps(data, indent=2)[:2000])
