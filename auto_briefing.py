"""
Claude API를 이용한 자동 브리핑 생성
Supabase에서 최신 시장 데이터를 읽어 자연스러운 한국어 브리핑 작성 후 저장
"""

import os
import json
from datetime import datetime, timedelta, timezone
from supabase import create_client
import anthropic

# =============================================
# 설정
# =============================================
SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# 브리핑 생성 모델 (비용 효율: haiku = 하루 약 $0.003, opus = 약 $0.02)
# 더 좋은 품질을 원하면 'claude-opus-4-6'으로 변경
BRIEFING_MODEL = 'claude-haiku-4-5'


# =============================================
# Supabase 데이터 수집
# =============================================

def fetch_market_tickers(client):
    """주요 지수 데이터 조회"""
    try:
        result = client.table('market_tickers').select('*').execute()
        return result.data or []
    except Exception as e:
        print(f"  시장 지수 조회 오류: {e}")
        return []


def fetch_fear_greed(client):
    """공포·탐욕 지수 조회"""
    try:
        result = client.table('fear_greed').select('*').order('updated_at', desc=True).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"  공포탐욕 조회 오류: {e}")
        return None


def fetch_macro_indicators(client):
    """매크로 지표 조회"""
    try:
        result = client.table('macro_indicators').select('*').execute()
        return result.data or []
    except Exception as e:
        print(f"  매크로 조회 오류: {e}")
        return []


def fetch_sector_performance(client):
    """섹터 퍼포먼스 조회 (1D 기준)"""
    try:
        result = client.table('sector_performance').select('*').execute()
        return result.data or []
    except Exception as e:
        print(f"  섹터 조회 오류: {e}")
        return []


def fetch_calendar_events(client):
    """오늘~3일 이내 경제 일정 조회"""
    try:
        result = client.table('calendar_events').select('*').order('event_date').limit(10).execute()
        return result.data or []
    except Exception as e:
        print(f"  캘린더 조회 오류: {e}")
        return []


def fetch_stock_prices(client):
    """주요 종목 시세 조회"""
    try:
        result = client.table('stock_prices').select('*').execute()
        return result.data or []
    except Exception as e:
        print(f"  종목 시세 조회 오류: {e}")
        return []


# =============================================
# 데이터 → 프롬프트 포맷
# =============================================

def format_market_data(tickers, fear_greed, macro, sectors, calendar, stocks):
    """수집한 데이터를 Claude에게 전달할 텍스트로 변환"""
    lines = []
    today_kst = datetime.now(timezone(timedelta(hours=9))).strftime('%Y년 %m월 %d일')
    lines.append(f"[날짜: {today_kst}]")
    lines.append("")

    # 주요 지수
    if tickers:
        lines.append("■ 주요 지수")
        for t in tickers:
            name = t.get('name', '')
            price = t.get('price', '')
            chg = t.get('change_pct', '')
            lines.append(f"  {name}: {price}  ({chg})")
        lines.append("")

    # 공포·탐욕 지수
    if fear_greed:
        val = fear_greed.get('value', '--')
        label = fear_greed.get('label', '')
        lines.append(f"■ 공포·탐욕 지수: {val} ({label})")
        lines.append("")

    # 매크로 지표
    if macro:
        lines.append("■ 매크로 지표")
        for m in macro:
            name = m.get('name', '')
            value = m.get('value', '')
            unit = m.get('unit', '')
            lines.append(f"  {name}: {value}{unit}")
        lines.append("")

    # 섹터 퍼포먼스 (1D 기준, 상위 3/하위 3)
    if sectors:
        sorted_sectors = sorted(sectors, key=lambda x: x.get('perf_1d', 0) or 0, reverse=True)
        lines.append("■ 섹터 퍼포먼스 (당일)")
        for s in sorted_sectors:
            name = s.get('sector_name', '')
            perf = s.get('perf_1d', 0) or 0
            sign = '+' if perf >= 0 else ''
            lines.append(f"  {name}: {sign}{perf:.2f}%")
        lines.append("")

    # 주요 종목 (미국 주식)
    us_stocks = [s for s in stocks if s.get('market') == 'US']
    if us_stocks:
        lines.append("■ 미국 주요 종목")
        for s in us_stocks:
            lines.append(f"  {s.get('name')}: {s.get('price')}  ({s.get('change_pct')})")
        lines.append("")

    # 주요 종목 (한국 주식)
    kr_stocks = [s for s in stocks if s.get('market') == 'KR']
    if kr_stocks:
        lines.append("■ 국내 주요 종목")
        for s in kr_stocks:
            lines.append(f"  {s.get('name')}: {s.get('price')}  ({s.get('change_pct')})")
        lines.append("")

    # 주요 종목 (암호화폐)
    crypto = [s for s in stocks if s.get('market') == 'CRYPTO']
    if crypto:
        lines.append("■ 주요 암호화폐")
        for s in crypto[:5]:  # 상위 5개만
            lines.append(f"  {s.get('name')}: {s.get('price')}  ({s.get('change_pct')})")
        lines.append("")

    # 경제 일정
    if calendar:
        lines.append("■ 주요 경제 일정")
        for ev in calendar[:6]:
            date = ev.get('event_date', '')
            name = ev.get('event_name', '')
            importance = '⭐' * min(int(ev.get('importance', 1)), 3)
            actual = ev.get('actual', '')
            forecast = ev.get('forecast', '')
            detail = f" (실제: {actual}, 예측: {forecast})" if actual or forecast else ""
            lines.append(f"  {date} {importance} {name}{detail}")
        lines.append("")

    return "\n".join(lines)


# =============================================
# Claude API 브리핑 생성
# =============================================

def generate_briefing(market_data_text: str) -> str:
    """Claude API로 자연스러운 브리핑 생성"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    system_prompt = """당신은 겁쟁이리서치의 시장 분석 전문가입니다.
매일 아침 투자자들을 위해 핵심 시장 데이터를 바탕으로 간결하고 통찰력 있는 브리핑을 작성합니다.

작성 원칙:
- 데이터를 단순 나열하지 말고, 흐름과 맥락을 해석해 주세요
- 투자자가 오늘 주목해야 할 핵심 포인트 2-3개를 뽑아 설명하세요
- 쉽고 친근한 한국어로 작성하되, 전문성을 유지하세요
- 공포탐욕지수, 섹터 강약, 주요 지수 흐름을 연결해 시장 분위기를 전달하세요
- 확인되지 않은 사실이나 예측은 명확히 구분해 주세요
- 길이: 300~500자 본문 + 핵심 포인트 정리"""

    user_prompt = f"""아래 시장 데이터를 바탕으로 오늘의 시장 브리핑을 작성해주세요.

{market_data_text}

다음 형식으로 작성해주세요:

[오늘의 시장 브리핑]
(2-3문단의 자연스러운 시장 해석)

[핵심 포인트]
• (포인트 1)
• (포인트 2)
• (포인트 3)"""

    response = client.messages.create(
        model=BRIEFING_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )

    return response.content[0].text


# =============================================
# HTML 변환
# =============================================

def briefing_to_html(briefing_text: str, market_data_text: str) -> str:
    """브리핑 텍스트를 HTML로 변환"""
    lines = briefing_text.split('\n')
    html_parts = []

    in_points = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('[') and line.endswith(']'):
            # 섹션 제목
            title = line[1:-1]
            html_parts.append(f'<h3 style="color:#94a3b8;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;margin:20px 0 10px;">{title}</h3>')
            in_points = '포인트' in title or 'point' in title.lower()
        elif line.startswith('•') or line.startswith('-'):
            # 글머리 기호
            content = line.lstrip('•- ').strip()
            html_parts.append(f'<div style="display:flex;gap:8px;margin:6px 0;"><span style="color:#60a5fa;flex-shrink:0;">•</span><span style="color:#cbd5e1;font-size:14px;line-height:1.7;">{content}</span></div>')
        else:
            # 일반 문단
            html_parts.append(f'<p style="font-size:14px;color:#cbd5e1;line-height:1.8;margin:8px 0;">{line}</p>')

    # 원본 데이터 (접을 수 있는 섹션)
    escaped_data = market_data_text.replace('<', '&lt;').replace('>', '&gt;')
    raw_data_html = f'''
<details style="margin-top:24px;border-top:1px solid #1e2030;padding-top:16px;">
  <summary style="cursor:pointer;color:#475569;font-size:12px;font-weight:600;letter-spacing:0.5px;">📊 원본 데이터 보기</summary>
  <pre style="font-size:11px;color:#475569;line-height:1.6;margin-top:12px;white-space:pre-wrap;">{escaped_data}</pre>
</details>'''

    generated_at = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
    footer = f'<p style="font-size:11px;color:#334155;margin-top:20px;border-top:1px solid #1e2030;padding-top:12px;">⚡ Claude AI 자동 생성 · {generated_at}</p>'

    return (
        '<div class="briefing">'
        + '\n'.join(html_parts)
        + raw_data_html
        + footer
        + '</div>'
    )


# =============================================
# Supabase 저장
# =============================================

def save_briefing(client, title: str, html_content: str):
    """오늘 브리핑 삭제 후 새로 저장"""
    today_start = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d') + 'T00:00:00'

    # 오늘 날짜 기존 브리핑 삭제 (중복 방지)
    existing = client.table('posts').select('id').eq('category', '📊 일일 브리핑').gte('created_at', today_start).execute()
    if existing.data:
        ids = [p['id'] for p in existing.data]
        client.table('posts').delete().in_('id', ids).execute()
        print(f"  기존 브리핑 {len(ids)}개 삭제")

    client.table('posts').insert({
        'category': '📊 일일 브리핑',
        'title': title,
        'content': html_content,
        'views': 0
    }).execute()
    print(f"  브리핑 저장 완료: {title}")


# =============================================
# 메인
# =============================================

def main():
    now_kst = datetime.now(timezone(timedelta(hours=9)))

    # 주말 제외 (선택 사항: 주말에도 생성하려면 아래 주석 처리)
    if now_kst.weekday() >= 5:
        day_name = ['월', '화', '수', '목', '금', '토', '일'][now_kst.weekday()]
        print(f"[{now_kst.strftime('%H:%M')}] {day_name}요일 — 브리핑 생략")
        return

    if not ANTHROPIC_API_KEY:
        print("오류: ANTHROPIC_API_KEY 환경 변수가 없습니다.")
        print("GitHub → Settings → Secrets → ANTHROPIC_API_KEY 를 등록해주세요.")
        return

    print(f"[{now_kst.strftime('%H:%M')}] 브리핑 생성 시작...")

    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  데이터 수집 중...")
    tickers = fetch_market_tickers(db)
    fear_greed = fetch_fear_greed(db)
    macro = fetch_macro_indicators(db)
    sectors = fetch_sector_performance(db)
    calendar = fetch_calendar_events(db)
    stocks = fetch_stock_prices(db)

    print("  데이터 포맷 중...")
    market_data_text = format_market_data(tickers, fear_greed, macro, sectors, calendar, stocks)
    print(market_data_text)

    print("  Claude API 브리핑 생성 중...")
    try:
        briefing_text = generate_briefing(market_data_text)
        print("  생성된 브리핑:")
        print(briefing_text)
    except Exception as e:
        print(f"  Claude API 오류: {e}")
        return

    print("  HTML 변환 중...")
    html_content = briefing_to_html(briefing_text, market_data_text)

    title = now_kst.strftime('%Y년 %m월 %d일') + ' 시장 브리핑'

    print("  Supabase 저장 중...")
    save_briefing(db, title, html_content)

    print(f"[완료] {title}")


if __name__ == '__main__':
    main()
