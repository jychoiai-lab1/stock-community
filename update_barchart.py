from patchright.sync_api import sync_playwright
from datetime import datetime
from supabase import create_client
import time

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'

BARCHART_URL = 'https://www.barchart.com/stocks/sectors/rankings'
BUCKET = 'images'
FILE_NAME = 'barchart_sectors.png'

def capture_and_upload():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  Barchart 섹터 퍼포먼스 캡처 중...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1400, 'height': 1800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        )
        page = context.new_page()
        page.goto(BARCHART_URL, wait_until='domcontentloaded', timeout=60000)
        time.sleep(5)

        # Matrix-Short Term 뷰 선택 (Today, 5-Day, 1-Month 표시)
        page.locator('select[name="timeFrame"]').select_option(label='Matrix-Short Term')
        time.sleep(5)

        # 팝업/광고/사이드바 제거
        page.evaluate("""() => {
            const toRemove = [
                '.bc-webinar-card',
                '.ab-iam-root',
                '.h-header',
                '.bc-header-premier-ads',
                '.left-hand-bar',
                '[class*="ab-iam"]',
                '[id="HW_frame_cont"]',
            ];
            toRemove.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        }""")
        time.sleep(1)

        # 매트릭스 테이블 위치로 clip 캡처
        el = page.query_selector('table.bc-major-market-sectors-table-matrix')
        if el:
            box = el.bounding_box()
            screenshot = page.screenshot(clip={
                'x': max(0, box['x'] - 5),
                'y': max(0, box['y'] - 5),
                'width': min(1400, box['width'] + 10),
                'height': box['height'] + 10
            })
        else:
            screenshot = page.screenshot(full_page=False)

        browser.close()

    print(f"  캡처 완료 ({len(screenshot):,} bytes)")

    # 디버그 스크린샷 저장
    with open('C:/Users/asdf/Pictures/Screenshots/barchart_final.png', 'wb') as f:
        f.write(screenshot)

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
    import traceback, sys, os
    LOG = r'C:\Users\asdf\webtest\logs\barchart.log'
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Barchart 섹터 퍼포먼스 업데이트 중...")
        capture_and_upload()
        print("Done!")
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] SUCCESS\n")
    except Exception as e:
        msg = traceback.format_exc()
        print(msg)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] ERROR\n{msg}\n")
        sys.exit(1)
