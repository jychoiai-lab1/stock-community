import json
from datetime import datetime
from scrapling.fetchers import Fetcher
from supabase import create_client

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

TARGET_COUNTRIES = {
    'USD': '미국',
    'JPY': '일본',
    'KRW': '한국',
}

FOMC_KEYWORDS = ['fomc', 'fed', 'federal reserve', 'interest rate', 'rate decision', 'monetary policy', 'powell']

FF_URLS = [
    'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
    'https://nfs.faireconomy.media/ff_calendar_nextweek.json',
]

def classify_type(title):
    if any(k in title.lower() for k in FOMC_KEYWORDS):
        return 'fomc'
    return 'indicator'

def fetch_and_save(client):
    all_events = []
    seen = set()

    for url in FF_URLS:
        try:
            page = Fetcher.get(url, stealthy_headers=True)
            if page.status != 200:
                print(f"  HTTP {page.status} ({url.split('/')[-1]})")
                continue

            events = json.loads(page.body)
            print(f"  {url.split('/')[-1]}: {len(events)} events")

            for ev in events:
                country_code = ev.get('country', '')
                if country_code not in TARGET_COUNTRIES:
                    continue
                if ev.get('impact', '') not in ('High', 'Medium'):
                    continue

                date_str = ev.get('date', '')[:10]
                title = ev.get('title', '').strip()
                if not date_str or not title:
                    continue

                key = f"{date_str}_{title}_{country_code}"
                if key in seen:
                    continue
                seen.add(key)

                all_events.append({
                    'event_date': date_str,
                    'title': f"[{TARGET_COUNTRIES[country_code]}] {title}",
                    'type': classify_type(title),
                })

        except Exception as e:
            print(f"  Error ({url.split('/')[-1]}): {e}")

    if not all_events:
        print("  No events to save")
        return

    today = datetime.now().strftime('%Y-%m-%d')
    client.table('events_calendar').delete().gte('event_date', today).execute()
    client.table('events_calendar').insert(all_events).execute()
    print(f"  Total {len(all_events)} events saved")

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Calendar updating...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    fetch_and_save(client)
    print("Done!")
