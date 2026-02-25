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
function createPostCard(post) {
  var preview = post.content.replace(/\n/g, ' ').slice(0, 80) + '...';
  return '<div class="post-card" onclick="openPost(' + post.id + ')"><div class="post-category">' + post.category + '</div><div class="post-title">' + post.title + '</div><div class="post-preview">' + preview + '</div><div class="post-meta"><span class="post-date">' + formatDate(post.created_at) + '</span><span class="post-stat">👁 ' + (post.views||0) + '</span></div></div>';
}
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
function openPost(id) {
  var post = allPosts.find(function(p){ return p.id === id; });
  if (!post) return;
  document.getElementById('modalContent').innerHTML = '<div class="modal-category">' + post.category + '</div><div class="modal-title">' + post.title + '</div><div class="modal-date">' + formatDate(post.created_at) + '</div><div class="modal-body">' + post.content.replace(/\n/g,'<br>') + '</div>';
  document.getElementById('modalOverlay').classList.add('active');
  document.body.style.overflow = 'hidden';
}
function closeModal() {
  document.getElementById('modalOverlay').classList.remove('active');
  document.body.style.overflow = '';
}
document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });
var tickers = {kospi:'2,650 +0.32%', kosdaq:'870 +0.78%', sp500:'5,123 +0.82%', nasdaq:'16,234 +1.21%', dow:'38,765 +0.35%'};
Object.keys(tickers).forEach(function(id){ var el=document.getElementById(id); if(el){el.textContent=tickers[id]; el.className='ticker-value up';} });
loadPosts();
