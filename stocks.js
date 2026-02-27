// ── 히트맵 이미지 강제 새로고침 ───────────────────────────────────────────────
function forceReloadImages() {
  var t = Date.now();
  document.querySelectorAll('.finviz-map-img').forEach(function(img) {
    var base = img.src.split('?')[0];
    img.src = '';
    setTimeout(function() { img.src = base + '?t=' + t; }, 50);
  });
}

// ── 갱신 버튼 상태 제어 ───────────────────────────────────────────────────────
function setRefreshBtn(state, msg) {
  var btn    = document.getElementById('refreshBtn');
  var txt    = document.getElementById('refreshBtnText');
  var status = document.getElementById('refreshStatus');
  if (state === 'ready')   { btn.disabled = false; btn.classList.remove('used','loading'); txt.textContent = '🔄 히트맵 갱신'; }
  if (state === 'loading') { btn.disabled = true;  btn.classList.add('loading');           txt.textContent = '⏳ 갱신 중...'; }
  if (state === 'used')    { btn.disabled = true;  btn.classList.remove('loading'); btn.classList.add('used'); txt.textContent = '✅ 갱신 완료'; }
  if (state === 'error')   { btn.disabled = true;  btn.classList.remove('loading'); btn.classList.add('used'); txt.textContent = '⚠️ 갱신 오류'; }
  if (status) status.textContent = msg || '';
}

// ── 3시간 쿨타임 ─────────────────────────────────────────────────────────────
var COOLDOWN_MS = 3 * 60 * 60 * 1000; // 3시간

function canPressRefresh() {
  var stored = localStorage.getItem('stockRefresh');
  if (!stored) return true;
  return Date.now() - new Date(JSON.parse(stored).pressedAt).getTime() >= COOLDOWN_MS;
}
function markRefreshUsed() {
  localStorage.setItem('stockRefresh', JSON.stringify({ pressedAt: new Date().toISOString() }));
}
function getRemainingMinutes() {
  var stored = localStorage.getItem('stockRefresh');
  if (!stored) return 0;
  var elapsed = Date.now() - new Date(JSON.parse(stored).pressedAt).getTime();
  return Math.ceil((COOLDOWN_MS - elapsed) / 60000);
}

// ── 갱신 버튼 클릭 핸들러 ────────────────────────────────────────────────────
async function handleRefresh() {
  if (!canPressRefresh()) return;
  if (!db) { setRefreshBtn('error', 'DB 연결 없음'); return; }

  markRefreshUsed();
  setRefreshBtn('loading', '요청 전송 중...');

  try {
    var ins = await db.from('refresh_trigger').insert({ status: 'pending' }).select().single();
    if (ins.error) throw ins.error;
    var triggerId = ins.data.id;
    setRefreshBtn('loading', '이미지 생성 중... (최대 3분 소요)');

    var attempts = 0;
    var poll = setInterval(async function() {
      attempts++;
      try {
        var res = await db.from('refresh_trigger').select('status').eq('id', triggerId).single();
        if (res.data) {
          if (res.data.status === 'done') {
            clearInterval(poll);
            forceReloadImages();
            setRefreshBtn('used', '히트맵이 업데이트됐습니다.');
          } else if (res.data.status === 'error') {
            clearInterval(poll);
            setRefreshBtn('error', '갱신 중 오류가 발생했습니다.');
          }
        }
      } catch(e) {}
      if (attempts >= 36) {
        clearInterval(poll);
        setRefreshBtn('error', '응답 시간 초과. 잠시 후 새로고침 해보세요.');
      }
    }, 5000);

  } catch(e) {
    setRefreshBtn('error', '요청 실패: ' + e.message);
  }
}

// ── 페이지 로드 시 버튼 초기 상태 설정 ───────────────────────────────────────
(function() {
  if (!canPressRefresh()) {
    var mins = getRemainingMinutes();
    var msg = mins >= 60
      ? Math.ceil(mins / 60) + '시간 후 갱신 가능'
      : mins + '분 후 갱신 가능';
    setRefreshBtn('used', msg);
  }
})();
