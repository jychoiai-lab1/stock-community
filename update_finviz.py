from patchright.sync_api import sync_playwright
from datetime import datetime
from supabase import create_client
import time

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

FINVIZ_URL = 'https://finviz.com/map.ashx?t=sec&st=d1'
BUCKET = 'images'
FILE_NAME = 'finviz_map.png'

def capture_and_upload():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  Finviz 맵 캡처 중...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1600, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.goto(FINVIZ_URL, wait_until='load', timeout=60000)
        time.sleep(5)  # 맵 완전 렌더링 대기

        # 맵 영역만 캡처
        screenshot = page.screenshot(full_page=False)
        browser.close()

    print(f"  캡처 완료 ({len(screenshot):,} bytes)")

    # Supabase Storage 업로드 (덮어쓰기)
    try:
        client.storage.from_(BUCKET).upload(
            FILE_NAME, screenshot, {'content-type': 'image/png'}
        )
    except Exception:
        client.storage.from_(BUCKET).update(
            FILE_NAME, screenshot, {'content-type': 'image/png'}
        )

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{FILE_NAME}"
    print(f"  업로드 완료: {public_url}")

if __name__ == '__main__':
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Finviz 맵 업데이트 중...")
    capture_and_upload()
    print("Done!")
