#!/usr/bin/env python3
import requests
import json

def test_api_direct():
    print("=== Testing API Direct Calls ===\n")
    
    try:
        # Test sailors-for-onwater endpoint
        print("1. Testing /api/sailors-for-onwater:")
        response = requests.get('http://localhost:5000/api/sailors-for-onwater')
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            if data.get('status') == 'success':
                columns = data.get('columns', [])
                print(f"   Number of columns: {len(columns)}")
                for i, col in enumerate(columns):
                    print(f"   Column {i+1}: {col.get('class_name')} (seq={col.get('sequence_number', 'N/A')}) - {len(col.get('sailors', []))} sailors")
            else:
                print(f"   Error: {data.get('message')}")
        else:
            print(f"   HTTP Error: {response.status_code}")
        
        print("\n2. Testing /api/race-status:")
        response = requests.get('http://localhost:5000/api/race-status')
        if response.status_code == 200:
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Race ID: {data.get('race_id')}")
            print(f"   Race Active: {data.get('race_active', 'N/A')}")
        else:
            print(f"   HTTP Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ERROR: Cannot connect to localhost:5000 - Flask app not running")
        print("   Start Flask with: C:/ProgramData/miniconda3/python.exe app.py")

if __name__ == "__main__":
    test_api_direct()