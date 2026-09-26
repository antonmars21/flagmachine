import requests
import json

# Test 1: Get sailors for onwater (no active race)
print("=== TEST 1: Get sailors (no active race) ===")
r = requests.get('http://localhost:5000/api/sailors-for-onwater')
data = r.json()
print(f"Status: {data.get('status')}")
print(f"Columns: {list(data.get('columns', {}).keys())}")
print(f"Column 1 count: {len(data.get('columns', {}).get('1', []))}")
print(f"Column 2 count: {len(data.get('columns', {}).get('2', []))}")
print(f"Column 3 count: {len(data.get('columns', {}).get('3', []))}")
print(f"Column 4 count: {len(data.get('columns', {}).get('4', []))}")

if data.get('columns', {}).get('1'):
    print(f"\nFirst sailor in column 1: {data['columns']['1'][0]}")

# Test 2: Start a race
print("\n=== TEST 2: Start race ===")

# Get all sailor UIDs
r = requests.get('http://localhost:5000/api/sailors-for-onwater')
data = r.json()
all_sailors = []
for col_sailors in data.get('columns', {}).values():
    all_sailors.extend([s['uid'] for s in col_sailors])

print(f"Total sailors: {len(all_sailors)}")

r = requests.post('http://localhost:5000/api/start-race', json={'selected_sailors': all_sailors[:5]})
start_data = r.json()
print(f"Start race response: {start_data}")
print(f"Race ID: {start_data.get('race_id')}")

# Test 3: Get sailors for active race
print("\n=== TEST 3: Get sailors for active race ===")
r = requests.get('http://localhost:5000/api/sailors-for-onwater')
data = r.json()
print(f"Column 1 count: {len(data.get('columns', {}).get('1', []))}")
print(f"Column 2 count: {len(data.get('columns', {}).get('2', []))}")
if data.get('columns', {}).get('1'):
    print(f"First sailor in column 1: {data['columns']['1'][0]}")
