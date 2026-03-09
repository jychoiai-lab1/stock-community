/* ══════════════════════════════════════════════
   겁쟁이리서치 — 대시보드 메인 JS
   ══════════════════════════════════════════════ */

// ── 상수 ──
const INDEX_ORDER = ['SPX','NDX','DJI','VIX','DXY','TNX','BTC','GOLD','OIL'];
const INDEX_FULL  = {
  SPX: 'S&P 500', NDX: 'NASDAQ', DJI: 'DOW',
  VIX: 'VIX', DXY: 'DXY', TNX: '10Y 금리',
  BTC: 'BTC', GOLD: 'GOLD', OIL: 'WTI Oil',
  USDJPY: 'USD/JPY',
};

const MACRO_LABELS = {
  sp500_pe:    { label: 'S&P500 PER',    unit: 'x'  },
  treasury_2y: { label: '2Y 국채금리',   unit: '%'  },
  treasury_10y:{ label: '10Y 국채금리',  unit: '%'  },
  treasury_30y:{ label: '30Y 국채금리',  unit: '%'  },
  vix:         { label: 'VIX 변동성',    unit: ''   },
};

const CAL_TYPE_LABEL = { fomc:'FOMC', earnings:'실적', indicator:'지표', general:'일정' };

let sectorData = [];
let sectorPeriod = 'day';

// ── 초기화 ──
document.addEventListener('DOMContentLoaded', () => {
  startClock();
  loadIndexCards();
  loadSectorPerformance();
  loadFearGreed();
  loadMacroStats();
  loadCalendar();
  loadStocks();

  // 5분마다 자동 갱신
  setInterval(() => {
    loadIndexCards();
    loadFearGreed();
  }, 5 * 60 * 1000);

  // 섹터 탭
  document.getElementById('sectorTabs').addEventListener('click', e => {
    const btn = e.target.closest('.pill');
    if (!btn) return;
    document.querySelectorAll('#sectorTabs .pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    sectorPeriod = btn.dataset.period;
    renderSectors();
  });

  // 종목 탭
  document.getElementById('marketTabs').addEventListener('click', e => {
    const btn = e.target.closest('.pill');
    if (!btn) return;
    document.querySelectorAll('#marketTabs .pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    loadStocks(btn.dataset.market);
  });
});

// ── 시계 ──
function startClock() {
  const el = document.getElementById('liveTime');
  const tick = () => {
    const now = new Date().toLocaleTimeString('ko-KR', {
      timeZone: 'Asia/Seoul',
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    });
    if (el) el.textContent = 'KST ' + now;
  };
  tick();
  setInterval(tick, 1000);
}

// ── 주요 지수 카드 ──
async function loadIndexCards() {
  try {
    const { data } = await db.from('market_ticker').select('*');
    if (!data || !data.length) return;

    const map = {};
    data.forEach(d => { map[d.symbol_key] = d; });

    const grid = document.getElementById('indexGrid');
    grid.innerHTML = '';

    // 지정 순서대로, 없으면 나머지
    const ordered = INDEX_ORDER.filter(k => map[k]);
    const rest = data.filter(d => !INDEX_ORDER.includes(d.symbol_key)).map(d => d.symbol_key);
    [...ordered, ...rest].forEach(key => {
      const d = map[key];
      if (!d) return;
      const isUp = d.is_up;
      const card = document.createElement('div');
      card.className = `index-card ${isUp ? 'up' : 'down'}`;
      card.innerHTML = `
        <div class="ic-name">${d.name}</div>
        <div class="ic-price">${d.price}</div>
        <div class="ic-change ${isUp ? 'up' : 'down'}">${isUp ? '▲' : '▼'} ${d.change_pct}</div>
      `;
      grid.appendChild(card);
    });

    const hint = document.getElementById('indexUpdateTime');
    if (hint) hint.textContent = '방금 갱신';
  } catch (e) {
    console.error('index cards:', e);
  }
}

// ── 섹터 퍼포먼스 ──
async function loadSectorPerformance() {
  try {
    const { data } = await db.from('sector_performance').select('*');
    if (!data || !data.length) {
      document.getElementById('sectorList').innerHTML =
        '<div class="empty-state">데이터를 업데이트 중입니다.<br>잠시 후 다시 확인해주세요.</div>';
      return;
    }
    sectorData = data;
    renderSectors();
  } catch (e) {
    console.error('sector:', e);
  }
}

function renderSectors() {
  const list = document.getElementById('sectorList');
  if (!sectorData.length) return;

  const key = sectorPeriod + '_pct';
  const sorted = [...sectorData].sort((a, b) => b[key] - a[key]);
  const maxAbs = Math.max(...sorted.map(s => Math.abs(s[key])), 0.01);

  list.innerHTML = sorted.map(s => {
    const pct = s[key] ?? 0;
    const isPos = pct >= 0;
    const barW = Math.min((Math.abs(pct) / maxAbs) * 100, 100);
    const sign = isPos ? '+' : '';
    return `
      <div class="sector-row">
        <div class="sector-name">${s.name}</div>
        <div class="sector-ticker">${s.ticker}</div>
        <div class="sector-bar-wrap">
          <div class="sector-bar ${isPos ? 'pos' : 'neg'}" style="width:${barW}%"></div>
        </div>
        <div class="sector-pct ${isPos ? 'pos' : 'neg'}">${sign}${pct.toFixed(2)}%</div>
      </div>`;
  }).join('');
}

// ── 공포·탐욕 ──
async function loadFearGreed() {
  try {
    const { data } = await db.from('fear_greed').select('*').order('updated_at', {ascending:false}).limit(1);
    if (!data || !data.length) return;
    const val = data[0].value;
    updateFearGreed(val);
  } catch (e) {
    console.error('fear greed:', e);
  }
}

function updateFearGreed(val) {
  const clamp = Math.max(0, Math.min(100, val));

  // 바늘 각도: 0(공포)=-90°, 50(중립)=0°, 100(탐욕)=90°
  const angle = -90 + clamp * 1.8;
  const rad   = (angle * Math.PI) / 180;
  const cx = 60, cy = 65, len = 42;
  const x2 = cx + len * Math.sin(rad);
  const y2 = cy - len * Math.cos(rad);
  const needle = document.getElementById('fgNeedle');
  if (needle) { needle.setAttribute('x2', x2.toFixed(1)); needle.setAttribute('y2', y2.toFixed(1)); }

  const valEl = document.getElementById('fgValue');
  const lblEl = document.getElementById('fgLabel');
  const updEl = document.getElementById('fgUpdated');

  if (valEl) valEl.textContent = clamp;
  if (lblEl) {
    let label, color;
    if      (clamp <= 25)  { label = '극도의 공포'; color = '#ff5252'; }
    else if (clamp <= 45)  { label = '공포';       color = '#ff8c42'; }
    else if (clamp <= 55)  { label = '중립';       color = '#f5a623'; }
    else if (clamp <= 75)  { label = '탐욕';       color = '#a8d97f'; }
    else                   { label = '극도의 탐욕'; color = '#00d97e'; }
    lblEl.textContent = label;
    lblEl.style.color = color;
    if (valEl) valEl.style.color = color;
  }
  if (updEl) {
    const now = new Date();
    updEl.textContent = `${now.toLocaleTimeString('ko-KR', {hour:'2-digit', minute:'2-digit'})} 기준`;
  }
}

// ── 매크로 지표 ──
async function loadMacroStats() {
  try {
    const { data } = await db.from('macro_indicators').select('*');
    const el = document.getElementById('macroStats');
    if (!el) return;
    if (!data || !data.length) {
      el.innerHTML = '<div class="empty-state">데이터 준비 중</div>';
      return;
    }
    const map = {};
    data.forEach(d => { map[d.key] = d; });

    const rows = Object.entries(MACRO_LABELS).map(([key, cfg]) => {
      const d = map[key];
      const val = d ? (d.value + (d.unit || cfg.unit || '')) : '—';
      return `
        <div class="macro-row">
          <div class="macro-key">${cfg.label}</div>
          <div class="macro-val">${val}</div>
        </div>`;
    }).join('');

    el.innerHTML = rows || '<div class="empty-state">데이터 없음</div>';
  } catch (e) {
    console.error('macro:', e);
  }
}

// ── 경제 캘린더 ──
async function loadCalendar() {
  try {
    const today = new Date().toISOString().slice(0, 10);
    const { data } = await db.from('events_calendar')
      .select('*')
      .gte('event_date', today)
      .order('event_date', { ascending: true })
      .limit(10);

    const el = document.getElementById('calendarList');
    if (!el) return;
    if (!data || !data.length) {
      el.innerHTML = '<div class="cal-empty">예정된 일정이 없습니다.</div>';
      return;
    }

    el.innerHTML = data.map(ev => {
      const type  = ev.type || 'general';
      const label = CAL_TYPE_LABEL[type] || '일정';
      const dateStr = new Date(ev.event_date + 'T00:00:00').toLocaleDateString('ko-KR', {
        month: 'short', day: 'numeric', weekday: 'short'
      });
      return `
        <div class="cal-item">
          <div class="cal-dot ${type}"></div>
          <div class="cal-body">
            <div class="cal-title">${escHtml(ev.title)}</div>
            <div class="cal-date">${dateStr}</div>
          </div>
          <div class="cal-badge ${type}">${label}</div>
        </div>`;
    }).join('');
  } catch (e) {
    console.error('calendar:', e);
  }
}

// ── 주요 종목 ──
let currentMarket = 'us';
async function loadStocks(market) {
  if (market) currentMarket = market;
  try {
    const { data } = await db.from('stock_prices')
      .select('*')
      .eq('market', currentMarket.toUpperCase())
      .limit(10);

    const el = document.getElementById('stockList');
    if (!el) return;
    if (!data || !data.length) {
      el.innerHTML = '<div class="empty-state">데이터 없음</div>';
      return;
    }

    const sorted = [...data].sort((a, b) => {
      const ap = parseFloat(a.change_pct) || 0;
      const bp = parseFloat(b.change_pct) || 0;
      return Math.abs(bp) - Math.abs(ap);
    });

    el.innerHTML = sorted.map(s => `
      <div class="stock-row">
        <div class="stock-info">
          <div class="stock-name">${escHtml(s.name)}</div>
          <div class="stock-ticker">${s.ticker}</div>
        </div>
        <div class="stock-right">
          <div class="stock-price">${s.price}</div>
          <div class="stock-change ${s.is_up ? 'up' : 'down'}">${s.is_up ? '▲' : '▼'} ${s.change_pct}</div>
        </div>
      </div>`).join('');
  } catch (e) {
    console.error('stocks:', e);
  }
}

// ── 유틸 ──
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}
