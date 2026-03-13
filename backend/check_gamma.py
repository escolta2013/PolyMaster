import requests
import json

def check_data():
    try:
        r = requests.get('https://gamma-api.polymarket.com/markets?limit=3&active=true&order=volume&ascending=false')
        data = r.json()
        for i, m in enumerate(data):
            print(f"--- Market {i} ---")
            print(f"Question: {m.get('question')}")
            print(f"Event: {json.dumps(m.get('event'), indent=2)}")
            print(f"Events: {m.get('events')}")
            print(f"Event Object: {m.get('event')}")
            print(f"Group: {m.get('group')}")
            if m.get('events') and isinstance(m.get('events'), list) and len(m.get('events')) > 0:
                print(f"First Event Title: {m.get('events')[0].get('title')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_data()
