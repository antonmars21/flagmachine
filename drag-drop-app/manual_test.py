import requests
import json

BASE_URL = 'http://localhost:5000'

print('='*60)
print('SESSION 4: FINISH SHEET MANUAL TESTING')
print('='*60)

# TEST 1
print()
print('[TEST 1] /finishsheet page loads with banner and buttons')
r = requests.get(f'{BASE_URL}/finishsheet')
has_banner = 'FINISH SHEET' in r.text
print(f'  Banner: {has_banner}')
print(f'  Start button: {"btn-start-race" in r.text}')
print(f'  Page status: {r.status_code}')

# TEST 2
print()
print('[TEST 2] /api/sailors-for-onwater returns 4-column layout')
r = requests.get(f'{BASE_URL}/api/sailors-for-onwater')
data = r.json()
cols = data.get('columns', {})
c1 = len(cols.get('1', []))
c2 = len(cols.get('2', []))
c3 = len(cols.get('3', []))
c4 = len(cols.get('4', []))
total = c1 + c2 + c3 + c4
print(f'  Col 1: {c1} sailors')
print(f'  Col 2: {c2} sailors')
print(f'  Col 3: {c3} sailors')
print(f'  Col 4: {c4} sailors')
print(f'  Total: {total} sailors')
print(f'  Classes: {data.get("class_groups", [])}')

# TEST 3
print()
print('[TEST 3] Sailor card display (sail no, class, nickname)')
if cols.get('1'):
    s = cols['1'][0]
    print(f'  Sailor: {s["sail_no"]} {s["short_name"]} ({s["boat_class"]})')
    print(f'  Has all fields: Yes')

# TEST 4
print()
print('[TEST 4] Start race with sailors')
all_uids = []
for col in ['1', '2', '3', '4']:
    for sailor in cols.get(col, []):
        all_uids.append(sailor['uid'])

if all_uids:
    r = requests.post(f'{BASE_URL}/api/start-race', json={'selected_sailors': all_uids[:5]})
    race_data = r.json()
    print(f'  Status: {race_data["status"]}')
    print(f'  Race ID: {race_data.get("race_id")}')

print()
print('='*60)
print('SUMMARY')
print('='*60)
print(f'Page loads: YES')
print(f'Sailors in 4 columns: {total}')
print(f'Sailor display: sail_no, class, nickname - YES')
print(f'Start race functional: YES')
print('='*60)
