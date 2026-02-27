#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update_kospi_map.py - 한국경제 코스피 마켓맵 캡처 후 Supabase Storage 업로드"""

from patchright.sync_api import sync_playwright
from datetime import datetime
from supabase import create_client
import time

SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = (
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.'
    'eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6'
    'InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.'
    'rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts'
)

HANKYUNG_URL = 'https://markets.hankyung.com/marketmap/kospi'
BUCKET = 'images'
FILE_NAME = 'kospi_map.png'
DEBUG_PATH = r'C:\Users\asdf\Pictures\Screenshots\kospi_map_debug.png'


def capture_and_upload():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  한국경제 코스피 마켓맵 캡처 중...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        page.goto(HANKYUNG_URL, wait_until='domcontentloaded', timeout=60000)

        # 맵 렌더링 대기
        time.sleep(5)

        # 불필요한 요소 제거 (헤더, 광고, 내비게이션)
        page.evaluate("""() => {
            const toRemove = [
                'header', 'nav', '.header', '.gnb', '.lnb',
                '.footer', 'footer', '.ad', '.advertisement',
                '.banner', '.popup', '.modal', '.cookie',
                '[class*="header"]', '[class*="nav"]',
                '[class*="footer"]', '[class*="ad-"]',
            ];
            toRemove.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        }""")
        time.sleep(1)

        # 마켓맵 컨테이너 탐색 (canvas, svg, 또는 지도 div)
        selectors = [
            'canvas',
            '#marketmap',
            '.marketmap',
            '[class*="marketmap"]',
            '[class*="market-map"]',
            '[id*="map"]',
            '.map-wrap',
            '#map',
        ]

        screenshot = None
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    box = el.bounding_box()
                    if box and box['width'] > 200 and box['height'] > 200:
                        screenshot = el.screenshot()
                        print(f"  요소 캡처 성공: {sel} ({box['width']:.0f}x{box['height']:.0f})")
                        break
            except Exception:
                continue

        if not screenshot:
            print("  개별 요소 캡처 실패 → 전체 페이지 캡처")
            screenshot = page.screenshot(full_page=False)

        browser.close()

    print(f"  캡처 완료 ({len(screenshot):,} bytes)")

    # 디버그용 로컬 저장
    try:
        with open(DEBUG_PATH, 'wb') as f:
            f.write(screenshot)
        print(f"  디버그 저장: {DEBUG_PATH}")
    except Exception as e:
        print(f"  디버그 저장 실패: {e}")

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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 코스피 마켓맵 업데이트 중...")
    capture_and_upload()
    print("Done!")
