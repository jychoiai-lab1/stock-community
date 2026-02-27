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
  return '<div class="post-card" onclick="openPost(' + post.id + ')">' +
    '<div class="post-category">' + post.category + '</div>' +
    '<div class="post-title">' + post.title + '</div>' +
    '<div class="post-preview">' + preview + '</div>' +
    '<div class="post-meta">' +
      '<span class="post-date">' + formatDate(post.created_at) + '</span>' +
      '<span style="display:flex;align-items:center;gap:10px;">' +
        '<span class="post-stat">👁 ' + (post.views||0) + '</span>' +
        '<button class="post-share-btn" onclick="event.stopPropagation();sharePost(' + post.id + ')">🔗</button>' +
      '</span>' +
    '</div>' +
  '</div>';
}

// ── 공유 기능 ─────────────────────────────────────────────────────────────────
function getShareUrl(postId) {
  var base = location.origin + location.pathname.split('?')[0].replace(/index\.html$/, '');
  return base + 'index.html?post=' + postId;
}
async function sharePost(id) {
  var post = allPosts.find(function(p){ return p.id === id; });
  var title = post ? post.title : '겁쟁이리서치';
  var url = getShareUrl(id);
  if (navigator.share) {
    try { await navigator.share({ title: title, url: url }); return; } catch(e) { if (e.name === 'AbortError') return; }
  }
  copyLink(url);
}
function copyLink(url) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(function() { showToast('링크가 복사됐습니다 🔗', 'success'); });
  } else {
    var el = document.createElement('textarea');
    el.value = url; el.style.cssText = 'position:fixed;opacity:0;';
    document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
    showToast('링크가 복사됐습니다 🔗', 'success');
  }
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
      var res = await db.from('posts').select('*').ilike('category', '%브리핑%').order('created_at', { ascending: false });
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
    // 공유 링크로 진입 시 해당 포스트 자동 오픈
    var sharedId = new URLSearchParams(location.search).get('post');
    if (sharedId) openPost(parseInt(sharedId));
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
async function openPost(id) {
  var post = allPosts.find(function(p){ return p.id === id; });
  // 메모리에 없으면 DB에서 직접 fetch (공유 링크로 진입 시)
  if (!post && db) {
    try {
      var res = await db.from('posts').select('*').eq('id', id).single();
      if (res.data) { post = res.data; allPosts.push(post); }
    } catch(e) {}
  }
  if (!post) return;
  document.getElementById('modalContent').innerHTML =
    '<div class="modal-category">' + post.category + '</div>' +
    '<div class="modal-title">' + post.title + '</div>' +
    '<div class="modal-date">' +
      '<span>' + formatDate(post.created_at) + '</span>' +
      '<button class="post-share-btn" onclick="sharePost(' + id + ')" style="font-size:13px;padding:4px 10px;">🔗 공유</button>' +
    '</div>' +
    '<div class="modal-body">' + post.content + '</div>';
  document.getElementById('modalOverlay').classList.add('active');
  document.body.style.overflow = 'hidden';
  setTimeout(initLWCharts, 100);
  // 조회수 +1
  var newViews = (post.views || 0) + 1;
  post.views = newViews;
  db.from('posts').update({ views: newViews }).eq('id', id).then(function() {
    var cards = document.querySelectorAll('.post-card');
    cards.forEach(function(card) {
      if (card.getAttribute('onclick') === 'openPost(' + id + ')') {
        var stat = card.querySelector('.post-stat');
        if (stat) stat.textContent = '👁 ' + newViews;
      }
    });
  });
}
function closeModal() {
  document.getElementById('modalOverlay').classList.remove('active');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });
var tickers = {kospi:'2,650 +0.32%', kosdaq:'870 +0.78%', sp500:'5,123 +0.82%', nasdaq:'16,234 +1.21%', dow:'38,765 +0.35%'};
Object.keys(tickers).forEach(function(id){ var el=document.getElementById(id); if(el){el.textContent=tickers[id]; el.className='ticker-value up';} });
loadPosts();

// 공포·탐욕 지수
async function loadFearGreed() {
  try {
    if (!db) return;
    var res = await db.from('fear_greed').select('*').order('updated_at', { ascending: false }).limit(1);
    if (res.error || !res.data || !res.data.length) return;
    var value = res.data[0].value;
    var updated_at = res.data[0].updated_at;
    var needle = document.getElementById('fgNeedle');
    var valEl = document.getElementById('fgValue');
    var labelEl = document.getElementById('fgLabel');
    var updEl = document.getElementById('fgUpdated');
    if (!needle) return;
    var theta = Math.PI - (value / 100) * Math.PI;
    var nx = (50 + 38 * Math.cos(theta)).toFixed(1);
    var ny = (54 - 38 * Math.sin(theta)).toFixed(1);
    needle.setAttribute('x2', nx);
    needle.setAttribute('y2', ny);
    var label, color;
    if (value <= 20) { label = '극도의 공포'; color = '#f87171'; }
    else if (value <= 40) { label = '공포'; color = '#fb923c'; }
    else if (value <= 60) { label = '중립'; color = '#fbbf24'; }
    else if (value <= 80) { label = '탐욕'; color = '#a3e635'; }
    else { label = '극도의 탐욕'; color = '#4ade80'; }
    valEl.textContent = value;
    valEl.style.color = color;
    labelEl.textContent = label;
    labelEl.style.color = color;
    if (updEl && updated_at) {
      var d = new Date(updated_at);
      updEl.textContent = (d.getMonth()+1) + '/' + d.getDate() + ' 업데이트';
    }
  } catch(e) { console.error('공포탐욕 오류:', e); }
}
loadFearGreed();

// 주요 일정 캘린더
async function loadEventsCalendar() {
  var list = document.getElementById('calList');
  if (!list) return;
  try {
    if (!db) { list.innerHTML = '<div class="cal-empty">연결 안됨</div>'; return; }
    var today = new Date().toISOString().split('T')[0];
    var futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 30);
    var future = futureDate.toISOString().split('T')[0];
    var res = await db.from('events_calendar').select('*').gte('event_date', today).lte('event_date', future).order('event_date').limit(8);
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) {
      list.innerHTML = '<div class="cal-empty">등록된 일정이 없어요</div>';
      return;
    }
    var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var TYPE_LABELS = { fomc:'FOMC', earnings:'실적', indicator:'지표', general:'기타' };
    list.innerHTML = res.data.map(function(e) {
      var d = new Date(e.event_date + 'T00:00:00');
      var typeLabel = TYPE_LABELS[e.type] || e.type;
      return '<div class="cal-item">' +
        '<div class="cal-date-badge"><span class="cal-month">' + MONTHS[d.getMonth()] + '</span><span class="cal-day">' + d.getDate() + '</span></div>' +
        '<div class="cal-info"><span class="cal-type ' + e.type + '">' + typeLabel + '</span><div class="cal-event-title">' + e.title + '</div></div>' +
        '</div>';
    }).join('');
  } catch(e) {
    list.innerHTML = '<div class="cal-empty">등록된 일정이 없어요</div>';
    console.error('캘린더 오류:', e);
  }
}
loadEventsCalendar();

// 오늘 방문자 카운트
async function loadVisitCount() {
  var el = document.getElementById('visitCount');
  if (!el || !db) return;
  try {
    var today = new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Seoul' });
    var storageKey = 'visited_' + today;
    // 오늘 처음 방문한 경우 카운트 증가
    if (!localStorage.getItem(storageKey)) {
      var res = await db.from('daily_visits').select('id, count').eq('date', today).single();
      if (res.data) {
        await db.from('daily_visits').update({ count: res.data.count + 1 }).eq('date', today);
      } else {
        await db.from('daily_visits').insert({ date: today, count: 1 });
      }
      localStorage.setItem(storageKey, '1');
    }
    // 최신 카운트 표시
    var res2 = await db.from('daily_visits').select('count').eq('date', today).single();
    if (res2.data) el.textContent = res2.data.count.toLocaleString();
  } catch(e) { console.error('방문자 오류:', e); }
}
loadVisitCount();

// 탭별 카테고리 포스트 로딩
var tabPostsLoaded = {};
var tabCategoryMap = {
  'us':     '🇺🇸 미국주식',
  'kr':     '🇰🇷 국내주식',
  'crypto': '🪙 암호화폐'
};

async function loadTabPosts(tabName) {
  var category = tabCategoryMap[tabName];
  console.log('[탭] loadTabPosts 시작:', tabName, '| 카테고리:', category, '| db:', !!db);
  if (!category) { console.log('[탭] category 없음'); return; }
  var listEl = document.getElementById(tabName + 'PostList');
  if (!listEl) { console.log('[탭] listEl 없음'); return; }
  listEl.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>불러오는 중...</p></div>';
  try {
    if (!db) throw new Error('DB 연결 안됨');
    console.log('[탭] Supabase 쿼리 시작...');
    var res = await db.from('posts').select('*').eq('category', category).order('created_at', { ascending: false });
    console.log('[탭] 쿼리 완료 | 오류:', res.error, '| 건수:', res.data && res.data.length);
    if (res.error) throw res.error;
    var posts = res.data || [];
    if (posts.length === 0) {
      listEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><div class="empty-state-text">아직 게시글이 없어요</div></div>';
    } else {
      posts.forEach(function(p) {
        if (!allPosts.find(function(ap){ return ap.id === p.id; })) allPosts.push(p);
      });
      listEl.innerHTML = posts.map(createPostCard).join('');
    }
    tabPostsLoaded[tabName] = true;
  } catch(e) {
    tabPostsLoaded[tabName] = false;
    listEl.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">오류: ' + e.message + '</div></div>';
    console.error('[탭] 오류:', e);
  }
}

// 탭 전환
function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(function(p) { p.style.display = 'none'; });
  document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
  document.getElementById('tab-' + name).style.display = '';
  btn.classList.add('active');
  console.log('[탭] switchTab:', name, '| loaded:', tabPostsLoaded[name]);
  if (!tabPostsLoaded[name] && tabCategoryMap[name]) {
    loadTabPosts(name);
  }
}
