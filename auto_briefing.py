"""
Claude API + 웹 검색을 이용한 자동 브리핑 생성
- Supabase에서 최신 시장 데이터 수집
- 급등락 섹터의 뉴스를 실시간 웹 검색으로 찾아 요약
- 남녀노소 누구나 이해하기 쉬운 한국어 브리핑 생성
"""

import os
from datetime import datetime, timedelta, timezone
from supabase import create_client
import anthropic

# =============================================
# 설정
# =============================================
SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ.rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# 웹 검색이 필요하므로 Sonnet 사용 (하루 약 $0.05, Haiku보다 검색 품질 좋음)
# 더 좋은 품질: 'claude-opus-4-6' / 더 저렴: 'claude-haiku-4-5' (검색 품질 낮음)
BRIEFING_MODEL = 'claude-sonnet-4-6'

# 섹터 이름 → 검색어 매핑 (영문 검색이 뉴스가 많음)
SECTOR_SEARCH_MAP = {
    '기술':        'Technology sector stocks XLK',
    '통신':        'Communication Services sector stocks XLC',
    '임의소비재':  'Consumer Discretionary sector stocks XLY',
    '금융':        'Financial sector stocks XLF',
    '산업재':      'Industrial sector stocks XLI',
    '헬스케어':    'Healthcare sector stocks XLV',
    '필수소비재':  'Consumer Staples sector stocks XLP',
    '소재':        'Materials sector stocks XLB',
    '에너지':      'Energy sector stocks XLE',
    '부동산':      'Real Estate sector stocks XLRE',
    '유틸리티':    'Utilities sector stocks XLU',
}


# =============================================
# Supabase 데이터 수집
# =============================================

def fetch_all_data(db):
    """Supabase에서 모든 필요한 데이터 한번에 수집"""
    data = {}

    try:
        r = db.table('market_tickers').select('*').execute()
        data['tickers'] = r.data or []
    except Exception as e:
        print(f"  지수 조회 오류: {e}")
        data['tickers'] = []

    try:
        r = db.table('fear_greed').select('*').order('updated_at', desc=True).limit(1).execute()
        data['fear_greed'] = r.data[0] if r.data else None
    except Exception as e:
        print(f"  공탐 조회 오류: {e}")
        data['fear_greed'] = None

    try:
        r = db.table('macro_indicators').select('*').execute()
        data['macro'] = r.data or []
    except Exception as e:
        print(f"  매크로 조회 오류: {e}")
        data['macro'] = []

    try:
        r = db.table('sector_performance').select('*').execute()
        data['sectors'] = r.data or []
    except Exception as e:
        print(f"  섹터 조회 오류: {e}")
        data['sectors'] = []

    try:
        r = db.table('calendar_events').select('*').order('event_date').limit(8).execute()
        data['calendar'] = r.data or []
    except Exception as e:
        print(f"  캘린더 조회 오류: {e}")
        data['calendar'] = []

    try:
        r = db.table('stock_prices').select('*').execute()
        data['stocks'] = r.data or []
    except Exception as e:
        print(f"  종목 조회 오류: {e}")
        data['stocks'] = []

    return data


# =============================================
# 주목할 섹터 판단
# =============================================

def get_notable_sectors(sectors, threshold=1.0):
    """당일 ±1% 이상 움직인 섹터 추출"""
    notable = []
    for s in sectors:
        perf = s.get('perf_1d', 0) or 0
        if abs(perf) >= threshold:
            notable.append({
                'name': s.get('sector_name', ''),
                'perf_1d': perf,
                'direction': '급등' if perf > 0 else '급락',
            })
    return sorted(notable, key=lambda x: abs(x['perf_1d']), reverse=True)


# =============================================
# 시장 데이터 → 텍스트 요약
# =============================================

def format_market_context(data):
    """Claude에게 전달할 시장 데이터 텍스트"""
    lines = []
    today_kst = datetime.now(timezone(timedelta(hours=9))).strftime('%Y년 %m월 %d일 (%A)')
    lines.append(f"오늘 날짜: {today_kst}")
    lines.append("")

    # 주요 지수
    if data['tickers']:
        lines.append("[주요 지수]")
        for t in data['tickers']:
            name = t.get('name', '')
            price = t.get('price', '')
            chg = t.get('change_pct', '')
            lines.append(f"  {name}: {price} ({chg})")
        lines.append("")

    # 공포·탐욕 지수
    if data['fear_greed']:
        val = data['fear_greed'].get('value', '--')
        label = data['fear_greed'].get('label', '')
        lines.append(f"[공포·탐욕 지수] {val}점 — {label}")
        lines.append("")

    # 매크로 지표
    if data['macro']:
        lines.append("[매크로 지표]")
        for m in data['macro']:
            lines.append(f"  {m.get('name')}: {m.get('value')}{m.get('unit','')}")
        lines.append("")

    # 섹터 퍼포먼스 전체
    if data['sectors']:
        sorted_s = sorted(data['sectors'], key=lambda x: x.get('perf_1d', 0) or 0, reverse=True)
        lines.append("[섹터 퍼포먼스 — 당일 등락률]")
        for s in sorted_s:
            perf = s.get('perf_1d', 0) or 0
            sign = '+' if perf >= 0 else ''
            lines.append(f"  {s.get('sector_name')}: {sign}{perf:.2f}%")
        lines.append("")

    # 미국 주요 종목
    us = [s for s in data['stocks'] if s.get('market') == 'US']
    if us:
        lines.append("[미국 주요 종목]")
        for s in us:
            lines.append(f"  {s.get('name')}: {s.get('price')} ({s.get('change_pct')})")
        lines.append("")

    # 국내 주요 종목
    kr = [s for s in data['stocks'] if s.get('market') == 'KR']
    if kr:
        lines.append("[국내 주요 종목]")
        for s in kr:
            lines.append(f"  {s.get('name')}: {s.get('price')} ({s.get('change_pct')})")
        lines.append("")

    # 암호화폐
    crypto = [s for s in data['stocks'] if s.get('market') == 'CRYPTO']
    if crypto:
        lines.append("[주요 암호화폐]")
        for s in crypto[:5]:
            lines.append(f"  {s.get('name')}: {s.get('price')} ({s.get('change_pct')})")
        lines.append("")

    # 경제 일정
    if data['calendar']:
        lines.append("[주요 경제 일정]")
        for ev in data['calendar'][:6]:
            importance = '⭐' * min(int(ev.get('importance', 1) or 1), 3)
            actual = ev.get('actual', '')
            forecast = ev.get('forecast', '')
            detail = f" → 실제 {actual} / 예측 {forecast}" if actual or forecast else ""
            lines.append(f"  {ev.get('event_date')} {importance} {ev.get('event_name')}{detail}")
        lines.append("")

    return "\n".join(lines)


# =============================================
# Claude API 브리핑 생성 (웹 검색 포함)
# =============================================

def generate_briefing(market_context: str, notable_sectors: list) -> str:
    """
    Claude Sonnet + 웹 검색으로 브리핑 생성
    - 급등락 섹터 뉴스를 실시간으로 검색
    - 누구나 이해하기 쉬운 한국어로 작성
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 주목할 섹터 목록 텍스트
    if notable_sectors:
        sector_focus = "특히 오늘 크게 움직인 섹터:\n"
        for s in notable_sectors[:4]:
            search_term = SECTOR_SEARCH_MAP.get(s['name'], s['name'] + ' sector')
            sector_focus += f"  - {s['name']} 섹터: {'+' if s['perf_1d'] > 0 else ''}{s['perf_1d']:.2f}% ({s['direction']}) → 검색어: \"{search_term} today news\"\n"
    else:
        sector_focus = "오늘은 섹터 전반적으로 큰 움직임이 없었습니다."

    system_prompt = """당신은 겁쟁이리서치의 시장 분석 전문가입니다.
투자를 처음 시작한 20대부터 뉴스를 꼼꼼히 읽는 60대까지, 누구나 이해할 수 있는 시장 브리핑을 작성합니다.

핵심 역할:
1. 오늘 시장 전반적인 분위기를 한눈에 파악할 수 있게 설명
2. 크게 오르거나 내린 섹터가 있다면, 웹 검색으로 그 이유를 찾아 쉽게 풀어 설명
3. 어려운 금융 용어는 괄호로 쉬운 설명을 추가 (예: PER(주가가 실적 대비 몇 배인지))
4. 오늘 꼭 알아야 할 중요 뉴스가 있다면 별도로 강조

웹 검색 사용 원칙:
- 급등락 섹터는 반드시 영어로 검색해 최신 뉴스를 찾아라 (예: "Energy sector XLE today news 2024")
- 전체 시장 분위기도 검색 가능 (예: "S&P 500 today market recap")
- 검색 결과에서 실제 뉴스 내용을 확인하고 한국어로 요약
- 검색된 뉴스 출처는 언급하지 않아도 됨 (내용만 요약)

작성 금지:
- "~같습니다", "~것으로 보입니다" 등 지나친 추측 표현
- 투자 권유나 매수/매도 조언
- 데이터에 없는 수치를 만들어내는 것"""

    user_prompt = f"""아래 시장 데이터를 바탕으로 오늘의 시장 브리핑을 작성해주세요.

=== 오늘의 시장 데이터 ===
{market_context}

=== 분석 포커스 ===
{sector_focus}

웹 검색으로 급등락 섹터의 원인이 된 뉴스를 찾은 후, 아래 형식으로 브리핑을 작성해주세요.

---

[📊 오늘의 시장 요약]
(전체 시장 분위기를 2-3문장으로. 지수 흐름 + 공포탐욕 지수를 연결해서 설명. 일반인도 이해하도록.)

[🔥 오늘의 섹터 이슈]
(급등하거나 급락한 섹터가 있다면, 그 이유를 뉴스와 함께 설명. 각 섹터당 2-4문장.)
(섹터 이름: **[섹터명] +X.XX% 급등** 또는 **[섹터명] -X.XX% 급락** 형식으로 시작)
(없으면 이 섹션 생략)

[📌 오늘의 핵심 포인트]
• (투자자가 오늘 꼭 알아야 할 것 1)
• (투자자가 오늘 꼭 알아야 할 것 2)
• (투자자가 오늘 꼭 알아야 할 것 3)

[🚨 놓치면 안 될 뉴스]
(오늘 시장에 큰 영향을 줄 수 있는 중요한 뉴스가 있다면 여기에. 없으면 이 섹션 생략.)

---
분량: 총 400~700자 (섹터 이슈 포함 시 더 길어도 됨)"""

    # 웹 검색 도구 설정
    tools = [
        {"type": "web_search_20260209", "name": "web_search"},
    ]

    # Claude API 호출 (웹 검색 자동 실행)
    response = client.messages.create(
        model=BRIEFING_MODEL,
        max_tokens=2048,
        system=system_prompt,
        tools=tools,
        messages=[{"role": "user", "content": user_prompt}]
    )

    # 텍스트 블록만 추출 (tool_use 블록 제외)
    result_text = ""
    for block in response.content:
        if block.type == "text":
            result_text += block.text

    return result_text.strip()


# =============================================
# 브리핑 텍스트 → HTML 변환
# =============================================

def briefing_to_html(briefing_text: str, market_context: str) -> str:
    """마크다운스러운 브리핑을 HTML로 변환"""

    def escape(s):
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    lines = briefing_text.split('\n')
    html_parts = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append('<div style="height:8px;"></div>')
            continue

        # --- 구분선
        if stripped.startswith('---'):
            continue

        # [섹션 제목]
        if stripped.startswith('[') and stripped.endswith(']'):
            title = stripped[1:-1]
            html_parts.append(
                f'<h3 style="font-size:14px;font-weight:700;color:#94a3b8;'
                f'margin:22px 0 10px;padding-bottom:6px;border-bottom:1px solid #1e2030;">'
                f'{escape(title)}</h3>'
            )
            continue

        # • 글머리 기호
        if stripped.startswith('•') or stripped.startswith('-'):
            content = stripped.lstrip('•- ').strip()
            # **굵게** 처리
            content = format_bold(escape(content))
            html_parts.append(
                f'<div style="display:flex;gap:10px;margin:7px 0;align-items:flex-start;">'
                f'<span style="color:#60a5fa;font-size:16px;line-height:1.4;flex-shrink:0;">•</span>'
                f'<span style="color:#cbd5e1;font-size:14px;line-height:1.75;">{content}</span>'
                f'</div>'
            )
            continue

        # **굵은 텍스트로 시작하는 줄 (섹터 이름 등)
        if stripped.startswith('**'):
            content = format_bold(escape(stripped))
            html_parts.append(
                f'<p style="font-size:14px;color:#e2e8f0;line-height:1.8;margin:10px 0 4px;">{content}</p>'
            )
            continue

        # 일반 문단
        content = format_bold(escape(stripped))
        html_parts.append(
            f'<p style="font-size:14px;color:#cbd5e1;line-height:1.8;margin:5px 0;">{content}</p>'
        )

    # 원본 데이터 접기
    escaped_raw = escape(market_context)
    raw_section = (
        '<details style="margin-top:28px;border-top:1px solid #1e2030;padding-top:14px;">'
        '<summary style="cursor:pointer;color:#475569;font-size:12px;font-weight:600;'
        'letter-spacing:0.5px;user-select:none;">📊 원본 시장 데이터 보기</summary>'
        f'<pre style="font-size:11px;color:#475569;line-height:1.6;margin-top:10px;'
        f'white-space:pre-wrap;word-break:break-word;">{escaped_raw}</pre>'
        '</details>'
    )

    generated_at = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
    footer = (
        f'<p style="font-size:11px;color:#334155;margin-top:16px;'
        f'border-top:1px solid #1e2030;padding-top:10px;">'
        f'⚡ Claude AI + 실시간 웹 검색 자동 생성 · {generated_at}</p>'
    )

    return (
        '<div class="briefing">'
        + '\n'.join(html_parts)
        + raw_section
        + footer
        + '</div>'
    )


def format_bold(text: str) -> str:
    """**텍스트** → <strong>텍스트</strong> 변환"""
    import re
    return re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#e2e8f0;">\1</strong>', text)


# =============================================
# Supabase 저장
# =============================================

def save_briefing(db, title: str, html_content: str):
    """오늘 날짜 기존 브리핑 삭제 후 새로 저장"""
    today_start = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d') + 'T00:00:00'

    existing = (
        db.table('posts')
        .select('id')
        .eq('category', '📊 일일 브리핑')
        .gte('created_at', today_start)
        .execute()
    )
    if existing.data:
        ids = [p['id'] for p in existing.data]
        db.table('posts').delete().in_('id', ids).execute()
        print(f"  기존 브리핑 {len(ids)}개 삭제")

    db.table('posts').insert({
        'category': '📊 일일 브리핑',
        'title': title,
        'content': html_content,
        'views': 0,
    }).execute()
    print(f"  저장 완료: {title}")


# =============================================
# 메인
# =============================================

def main():
    now_kst = datetime.now(timezone(timedelta(hours=9)))

    if now_kst.weekday() >= 5:
        day = ['월', '화', '수', '목', '금', '토', '일'][now_kst.weekday()]
        print(f"[{now_kst.strftime('%H:%M')}] {day}요일 — 브리핑 생략")
        return

    if not ANTHROPIC_API_KEY:
        print("오류: ANTHROPIC_API_KEY 환경 변수가 없습니다.")
        print("GitHub → Settings → Secrets and variables → Actions → ANTHROPIC_API_KEY 등록 필요")
        return

    print(f"[{now_kst.strftime('%H:%M')}] 브리핑 생성 시작...")

    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("  Supabase 데이터 수집 중...")
    data = fetch_all_data(db)

    print("  데이터 포맷 중...")
    market_context = format_market_context(data)

    # 급등락 섹터 파악
    notable_sectors = get_notable_sectors(data['sectors'], threshold=1.0)
    if notable_sectors:
        print(f"  주목 섹터 {len(notable_sectors)}개: {[s['name'] for s in notable_sectors]}")
    else:
        print("  섹터 변동 미미 — 전반적 분위기 중심으로 작성")

    print("  Claude API + 웹 검색으로 브리핑 생성 중... (20~40초 소요)")
    try:
        briefing_text = generate_briefing(market_context, notable_sectors)
        print("\n=== 생성된 브리핑 ===")
        print(briefing_text)
        print("===================\n")
    except Exception as e:
        print(f"  Claude API 오류: {e}")
        import traceback
        traceback.print_exc()
        return

    print("  HTML 변환 중...")
    html_content = briefing_to_html(briefing_text, market_context)

    title = now_kst.strftime('%Y년 %m월 %d일') + ' 시장 브리핑'

    print("  Supabase 저장 중...")
    save_briefing(db, title, html_content)

    print(f"\n[완료] '{title}' 저장 완료!")


if __name__ == '__main__':
    main()
