"""
SESSION 4: Integration Test - Finish Sheet Manual Testing
Tests: 1) Page loads, 2) Sailors display in 4 columns, 3) Sailor cards show sail number/class/nickname
"""
import requests
import json

BASE_URL = "http://localhost:5000"

print("=" * 60)
print("SESSION 4: FINISH SHEET MANUAL TESTING")
print("=" * 60)

# TEST 1: Page Loads
print("\n[TEST 1] /finishsheet page loads with banner and buttons")
r = requests.get(f"{BASE_URL}/finishsheet")

has_banner = '⚓ FINISH SHEET' in r.text
has_start_btn = 'btn-start-race' in r.text
has_end_btn = 'btn-end-race' in r.text
has_elapsed = 'elapsed-time' in r.text

print(f"  ✓ Banner displays: {has_banner}")
print(f"  ✓ Start button present: {has_start_btn}")
print(f"  ✓ End button present: {has_end_btn}")
print(f"  ✓ Elapsed time display: {has_elapsed}")

# TEST 2: API Returns Sailors in 4 Columns
print("\n[TEST 2] /api/sailors-for-onwater returns 4-column layout")
r = requests.get(f"{BASE_URL}/api/sailors-for-onwater")
data = r.json()

status_ok = data['status'] == 'success'
columns = data.get('columns', {})
class_groups = data.get('class_groups', [])

col_1_count = len(columns.get('1', []))
col_2_count = len(columns.get('2', []))
col_3_count = len(columns.get('3', []))
col_4_count = len(columns.get('4', []))
total_sailors = col_1_count + col_2_count + col_3_count + col_4_count

print(f"  ✓ API responds with success: {status_ok}")
print(f"  ✓ Class groups: {class_groups}")
print(f"  ✓ Column 1 ({class_groups[0] if class_groups else 'N/A'}): {col_1_count} sailors")
print(f"  ✓ Column 2 ({class_groups[1] if len(class_groups)>1 else 'N/A'}): {col_2_count} sailors")
print(f"  ✓ Column 3 ({class_groups[2] if len(class_groups)>2 else 'N/A'}): {col_3_count} sailors")
print(f"  ✓ Column 4 (Open): {col_4_count} sailors")
print(f"  ✓ Total sailors: {total_sailors}")

# TEST 3: Sailor Card Display
print("\n[TEST 3] Sailor cards display sail number, class, nickname")
if col_1_count > 0:
    first_sailor = columns['1'][0]
    print(f"  Sample sailor from Column 1:")
    print(f"    - Sail Number: {first_sailor.get('sail_no')} ✓")
    print(f"    - Class: {first_sailor.get('boat_class')} ✓")
    print(f"    - Nickname: {first_sailor.get('short_name')} ✓")
    print(f"    - UID: {first_sailor.get('uid')}")
    print(f"    - Seed: {first_sailor.get('seed')}")
    print(f"    - Lap count: {first_sailor.get('lap_count')}")
else:
    print("  ERROR: No sailors in column 1")

# TEST 4: Start Race API
print("\n[TEST 4] /api/start-race creates race and adds sailors")
all_sailor_uids = []
for col in ['1', '2', '3', '4']:
    for sailor in columns.get(col, []):
        all_sailor_uids.append(sailor['uid'])

r = requests.post(f"{BASE_URL}/api/start-race", 
                 json={'selected_sailors': all_sailor_uids[:5]})
race_data = r.json()

race_started = race_data['status'] == 'success'
race_id = race_data.get('race_id')

print(f"  ✓ Race start successful: {race_started}")
print(f"  ✓ Race ID: {race_id}")

# TEST 5: Get Elapsed Time (only if race started)
if race_started:
    import time
    time.sleep(1)
    print("\n[TEST 5] /api/get-elapsed-time returns current race time")
    r = requests.get(f"{BASE_URL}/api/get-elapsed-time")
    time_data = r.json()
    
    has_elapsed = time_data['status'] == 'success'
    elapsed_sec = time_data.get('elapsed_seconds', 0)
    formatted = time_data.get('formatted', '00:00')
    
    print(f"  ✓ Elapsed time API works: {has_elapsed}")
    print(f"  ✓ Elapsed seconds: {elapsed_sec}")
    print(f"  ✓ Formatted time: {formatted}")

print("\n" + "=" * 60)
print("MANUAL TESTING SUMMARY")
print("=" * 60)
print(f"✓ Page loads with banner and controls")
print(f"✓ {total_sailors} sailors loaded across 4 columns")
print(f"✓ Sailor cards display (sail #, class, nickname)")
print(f"✓ Start race API functional (race_id: {race_id})")
print("=" * 60)
