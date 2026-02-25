var samplePosts = [
  { id: 1, category: '📊 아침 브리핑', title: '2026년 2월 25일 아침 주식 브리핑',
    content: '안녕하세요! 오늘의 주식 브리핑입니다.\n\n🇺🇸 미국 시장\n- S&P 500: 5,123 (+0.82%)\n- 나스닥: 16,234 (+1.21%)\n- 테슬라: $280.50 (-0.5%)\n- 애플: $215.30 (+0.8%)\n\n🇰🇷 한국 시장\n- 코스피: 2,650 (+0.32%)\n- 삼성전자: 72,000원 (+1.11%)\n\n💡 오늘의 포인트\n미국 증시는 연준의 금리 동결 기대감에 상승 마감했습니다.',
    created_at: '2026-02-25T08:00:00', views: 142 },
  { id: 2, category: '📊 아침 브리핑', title: '2026년 2월 24일 아침 주식 브리핑',
    content: '안녕하세요! 오늘의 주식 브리핑입니다.\n\n🇺🇸 미국 시장\n- S&P 500: 5,081 (-0.45%)\n- 나스닥: 16,040 (-0.82%)\n\n🇰🇷 한국 시장\n- 코스피: 2,641 (-0.18%)\n\n💡 오늘의 포인트\nPCE 물가 지수가 예상치를 소폭 상회하면서 금리 인하 기대감이 약해졌습니다.',
    created_at: '2026-02-24T08:00:00', views: 98 }
];
function formatDate(d) {
  var dt = new Date(d), now = new Date(), diff = Math.floor((now - dt) / 60000);
  if (diff < 60) return diff + '분 전';
  if (diff < 1440) return Math.floor(diff/60) + '시간 전';
  return dt.getFullYear() + '.' + String(dt.getMonth()+1).padStart(2,'0') + '.' + String(dt.getDate()).padStart(2,'0');
}
function stripHtml(html) {
  return html.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}
function createPostCard(post) {
  var preview = stripHtml(post.content).slice(0, 80) + '...';
  return '<div class="post-card" onclick="openPost(' + post.id + ')"><div class="post-category">' + post.category + '</div><div class="post-title">' + post.title + '</div><div class="post-preview">' + preview + '</div><div class="post-meta"><span class="post-date">' + formatDate(post.created_at) + '</span><span class="post-stat">👁 ' + (post.views||0) + '</span></div></div>';
}
async function loadTicker() {
  var tape = document.getElementById('tickerTrack');
  if (!tape) return;
  try {
    var res = await db.from('market_ticker').select('*').order('id');
    if (res.error || !res.data || !res.data.length) return;
    var items = res.data.map(function(t) {
      var cls = t.is_up ? 'up' : 'down';
      var arrow = t.is_up ? '▲' : '▼';
      return '<span class="ticker-item">' +
        '<span class="ticker-name">' + t.name + '</span>' +
        '<span class="ticker-price">' + t.price + '</span>' +
        '<span class="ticker-chg ' + cls + '">' + arrow + ' ' + t.change_pct + '</span>' +
        '</span>';
    }).join('');
    tape.innerHTML = items + items; // 무한 루프를 위해 2번 반복
  } catch(e) { console.error('티커 오류:', e); }
}
loadTicker();
setInterval(loadTicker, 60 * 60 * 1000); // 1시간마다 자동 갱신

async function openPostByDate(dateStr) {
  var parts = dateStr.split('-');
  var korDate = parts[0] + '년 ' + parts[1] + '월 ' + parts[2] + '일';
  // allPosts에서 먼저 검색
  var post = allPosts.find(function(p) { return p.title && p.title.includes(korDate); });
  if (post) { openPost(post.id); return; }
  // 없으면 전체 다시 불러와서 검색
  try {
    var res = await db.from('posts').select('*').order('created_at', { ascending: false });
    if (res.data && res.data.length) {
      allPosts = res.data;
      var found = allPosts.find(function(p) { return p.title && p.title.includes(korDate); });
      if (found) { openPost(found.id); }
    }
  } catch(e) { console.error('포스트 검색 오류:', e); }
}

async function loadSpecialTickers() {
  var list = document.getElementById('specialTickerList');
  if (!list) return;
  try {
    var res = await db.from('special_tickers').select('*').order('first_date', { ascending: false });
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) {
      list.innerHTML = '<div class="sidebar-empty">아직 없음</div>';
      return;
    }
    list.innerHTML = res.data.map(function(t) {
      var d = t.first_date ? t.first_date.replace(/-/g, '.') : '';
      return '<div class="sidebar-ticker" onclick="openPostByDate(\'' + t.first_date + '\')">' +
        '<div class="sidebar-ticker-top">' +
          '<span class="sidebar-ticker-symbol">' + t.ticker + '</span>' +
          '<span class="sidebar-ticker-date">' + d + '</span>' +
        '</div>' +
        '<span class="sidebar-ticker-name">' + t.name + '</span>' +
        '</div>';
    }).join('');
  } catch(e) { console.error('특별종목 오류:', e); }
}
loadSpecialTickers();

var allPosts = [];
async function loadPosts() {
  var postList = document.getElementById('postList');
  var postsCount = document.getElementById('postsCount');
  try {
    if (db) {
      var res = await db.from('posts').select('*').order('created_at', { ascending: false });
      if (res.error) throw res.error;
      allPosts = res.data || [];
    } else {
      await new Promise(r => setTimeout(r, 600));
      allPosts = samplePosts;
    }
    if (allPosts.length === 0) {
      postList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><div class="empty-state-text">아직 게시글이 없어요</div></div>';
    } else {
      postList.innerHTML = allPosts.map(createPostCard).join('');
      postsCount.textContent = '총 ' + allPosts.length + '개';
    }
  } catch(err) {
    postList.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">오류: ' + err.message + '</div></div>';
  }
}
async function initLWCharts() {
  var els = document.querySelectorAll('.lw-chart');
  if (!els.length) return;
  var keys = Array.from(els).map(function(el){ return el.getAttribute('data-key'); }).filter(Boolean);
  if (!keys.length) return;
  try {
    var res = await db.from('chart_data').select('ticker_key,ohlcv').in('ticker_key', keys);
    if (res.error) throw res.error;
    var dataMap = {};
    (res.data || []).forEach(function(row){ dataMap[row.ticker_key] = row.ohlcv; });
    els.forEach(function(el) {
      var key = el.getAttribute('data-key');
      var ohlcv = dataMap[key];
      if (!ohlcv) { el.innerHTML = '<div style="color:#64748b;padding:12px;font-size:13px;">차트 데이터 없음</div>'; return; }
      el.innerHTML = '';
      var chart = LightweightCharts.createChart(el, {
        width: el.clientWidth,
        height: 300,
        layout: { background: { color: '#0e1117' }, textColor: '#94a3b8' },
        grid: { vertLines: { color: '#1e2535' }, horzLines: { color: '#1e2535' } },
        crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
        rightPriceScale: { borderColor: '#2d3748' },
        timeScale: { borderColor: '#2d3748', timeVisible: true },
      });
      var candleSeries = chart.addCandlestickSeries({
        upColor: '#f87171', downColor: '#60a5fa',
        borderUpColor: '#f87171', borderDownColor: '#60a5fa',
        wickUpColor: '#f87171', wickDownColor: '#60a5fa',
      });
      candleSeries.setData(ohlcv.candles || []);
      if (ohlcv.ema20 && ohlcv.ema20.length) {
        var ema20Series = chart.addLineSeries({ color: '#facc15', lineWidth: 1, priceLineVisible: false });
        ema20Series.setData(ohlcv.ema20);
      }
      if (ohlcv.ema50 && ohlcv.ema50.length) {
        var ema50Series = chart.addLineSeries({ color: '#a78bfa', lineWidth: 1, priceLineVisible: false });
        ema50Series.setData(ohlcv.ema50);
      }
      chart.timeScale().fitContent();
      var ro = new ResizeObserver(function(){ chart.applyOptions({ width: el.clientWidth }); chart.timeScale().fitContent(); });
      ro.observe(el);
    });
  } catch(err) {
    console.error('차트 로딩 오류:', err);
  }
}
function openPost(id) {
  var post = allPosts.find(function(p){ return p.id === id; });
  if (!post) return;
  document.getElementById('modalContent').innerHTML =
    '<div class="modal-category">' + post.category + '</div>' +
    '<div class="modal-title">' + post.title + '</div>' +
    '<div class="modal-date">' + formatDate(post.created_at) + '</div>' +
    '<div class="modal-body">' + post.content + '</div>';
  document.getElementById('modalOverlay').classList.add('active');
  document.body.style.overflow = 'hidden';
  setTimeout(initLWCharts, 100);
}
function closeModal() {
  document.getElementById('modalOverlay').classList.remove('active');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });
var tickers = {kospi:'2,650 +0.32%', kosdaq:'870 +0.78%', sp500:'5,123 +0.82%', nasdaq:'16,234 +1.21%', dow:'38,765 +0.35%'};
Object.keys(tickers).forEach(function(id){ var el=document.getElementById(id); if(el){el.textContent=tickers[id]; el.className='ticker-value up';} });
loadPosts();
