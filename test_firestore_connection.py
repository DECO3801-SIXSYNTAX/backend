import os
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SiPanit.settings')
BASE_DIR = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(BASE_DIR))

django.setup()

print("="*60)
print("FIRESTORE CONNECTION TEST")
print("="*60)

from SiPanit.firebase import get_db
from google.cloud import firestore

try:
    print("\n1. Getting Firestore client...")
    db = get_db()
    print("   ✅ Firestore client created")
    
    print("\n2. Testing simple query (list collections)...")
    collections = list(db.collections())
    print(f"   ✅ Found {len(collections)} collections:")
    for col in collections:
        print(f"      - {col.id}")
    
    print("\n3. Testing events collection...")
    events_ref = db.collection('events')
    
    print("   Fetching first event...")
    events = list(events_ref.limit(1).stream())
    
    if events:
        event = events[0]
        print(f"   ✅ Found event: {event.id}")
        print(f"      Data: {event.to_dict()}")
    else:
        print("   ⚠️  No events found in collection")
    
    print("\n4. Testing specific event...")
    event_id = "MoBknbB0zkyIifGrKwdg"
    print(f"   Fetching event: {event_id}")
    
    event_doc = db.collection('events').document(event_id).get()
    
    if event_doc.exists:
        print(f"   ✅ Event exists!")
        data = event_doc.to_dict()
        print(f"      Name: {data.get('name')}")
        print(f"      Keys: {list(data.keys())}")
    else:
        print(f"   ❌ Event does not exist")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("="*60)
