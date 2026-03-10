import requests
from datetime import datetime
from supabase import create_client

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

CNN_URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'

def update_fear_greed(client):
    resp = requests.get(CNN_URL, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    resp.raise_for_status()
    data = resp.json()
    fg = data['fear_and_greed']

    score = int(round(float(fg['score'])))
    rating = fg['rating']

    client.table('fear_greed').update({
        'value': score,
        'updated_at': datetime.utcnow().isoformat()
    }).eq('id', 1).execute()

    print(f"  CNN Fear & Greed: {score} ({rating})")

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fear & Greed updating...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    update_fear_greed(client)
    print("Done!")
