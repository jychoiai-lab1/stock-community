import requests
from datetime import datetime
from supabase import create_client

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

# 미국/일본/한국만 필터
TARGET_COUNTRIES = {
    'USD': ('US', '미국'),
    'JPY': ('JP', '일본'),
    'KRW': ('KR', '한국'),
}

FOMC_KEYWORDS = ['fomc', 'fed', 'federal reserve', 'interest rate', 'rate decision', 'monetary policy', 'powell']

FF_URLS = [
    'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
]

def classify_type(title):
    t = title.lower()
    if any(k in t for k in FOMC_KEYWORDS):
        return 'fomc'
    return 'indicator'

def parse_date(date_str):
    # "2026-02-22T16:45:00-05:00" -> "2026-02-22"
    try:
        return date_str.strip()[:10]
    except:
        return None

def fetch_and_save(client):
    all_events = []
    seen = set()

    for url in FF_URLS:
        try:
            r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200:
                print(f"  HTTP {r.status_code} ({url.split('/')[-1]})")
                continue
            events = r.json()
            print(f"  {url.split('/')[-1]}: {len(events)} events")

            for ev in events:
                country_code = ev.get('country', '')
                if country_code not in TARGET_COUNTRIES:
                    continue
                impact = ev.get('impact', '')
                if impact not in ('High', 'Medium'):
                    continue

                date_str = parse_date(ev.get('date', ''))
                if not date_str:
                    continue

                title = ev.get('title', '').strip()
                _, country_label = TARGET_COUNTRIES[country_code]

                key = f"{date_str}_{title}_{country_code}"
                if key in seen:
                    continue
                seen.add(key)

                all_events.append({
                    'event_date': date_str,
                    'title': f"[{country_label}] {title}",
                    'type': classify_type(title),
                })

        except Exception as e:
            print(f"  Error ({url}): {e}")

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
