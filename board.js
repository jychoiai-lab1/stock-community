var boardPosts = [];
var lastPostTime = 0;
var lastCommentTime = 0;
var POST_COOLDOWN = 30000;
var COMMENT_COOLDOWN = 10000;

function formatDate(d) {
  var dt = new Date(d), now = new Date(), diff = Math.floor((now - dt) / 60000);
  if (diff < 1) return '방금 전';
  if (diff < 60) return diff + '분 전';
  if (diff < 1440) return Math.floor(diff / 60) + '시간 전';
  return dt.getFullYear() + '.' + String(dt.getMonth()+1).padStart(2,'0') + '.' + String(dt.getDate()).padStart(2,'0');
}

function escapeHtml(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/\n/g,'<br>');
}

function onPostInput() {
  var el = document.getElementById('boardContent');
  var count = el.value.length;
  document.getElementById('charCount').textContent = count + ' / 300';
  document.getElementById('charCount').style.color = count > 270 ? '#f87171' : '';
}

// ── 게시글 목록 로드 ──────────────────────────────────────────────────────────
async function loadBoard() {
  var list = document.getElementById('boardList');
  try {
    var res = await db.from('board_posts').select('*, board_comments(count)').order('created_at', { ascending: false });
    if (res.error) throw res.error;
    boardPosts = res.data || [];
    if (!boardPosts.length) {
      list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💬</div><div class="empty-state-text">첫 번째 글을 남겨보세요!</div></div>';
      return;
    }
    list.innerHTML = boardPosts.map(function(p) {
      var commentCount = (p.board_comments && p.board_comments[0]) ? p.board_comments[0].count : 0;
      var liked = !!localStorage.getItem('liked_' + p.id);
      return '<div class="board-card" id="bcard-' + p.id + '">' +
        '<div class="board-card-header">' +
          '<span class="board-nickname">' + escapeHtml(p.nickname) + '</span>' +
          '<span class="board-time">' + formatDate(p.created_at) + '</span>' +
        '</div>' +
        '<div class="board-card-content">' + escapeHtml(p.content) + '</div>' +
        '<div class="board-card-footer">' +
          '<button class="board-like' + (liked ? ' liked' : '') + '" onclick="likePost(' + p.id + ')">❤️ ' + (p.likes || 0) + '</button>' +
          '<button class="board-comment-btn" onclick="toggleComments(' + p.id + ')">💬 댓글 ' + commentCount + '</button>' +
          '<button class="post-share-btn" onclick="shareBoardPost(' + p.id + ')" style="margin-left:auto;">🔗</button>' +
        '</div>' +
        '<div class="board-comments-wrap" id="comments-' + p.id + '" style="display:none;">' +
          '<div class="board-comments-list" id="clist-' + p.id + '"></div>' +
          '<div class="board-comment-form">' +
            '<input type="text" class="board-input" id="cnick-' + p.id + '" placeholder="닉네임" maxlength="20" style="margin-bottom:6px;" />' +
            '<input type="password" class="board-input" id="cpw-' + p.id + '" placeholder="비밀번호 (수정·삭제 시 필요)" maxlength="20" style="margin-bottom:6px;" />' +
            '<textarea class="board-contenteditable" id="ctxt-' + p.id + '" placeholder="댓글을 입력하세요" maxlength="200" style="resize:none;height:70px;"></textarea>' +
            '<button class="board-submit" style="margin-top:8px;width:100%;" onclick="submitComment(' + p.id + ')">댓글 등록</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">불러오기 실패: ' + escapeHtml(e.message) + '</div></div>';
  }
}

// ── 댓글 토글 ────────────────────────────────────────────────────────────────
async function toggleComments(postId) {
  var wrap = document.getElementById('comments-' + postId);
  if (wrap.style.display === 'none') {
    wrap.style.display = 'block';
    await loadComments(postId);
  } else {
    wrap.style.display = 'none';
  }
}

// ── 댓글 목록 로드 ────────────────────────────────────────────────────────────
async function loadComments(postId) {
  var clist = document.getElementById('clist-' + postId);
  clist.innerHTML = '<div style="color:#475569;font-size:13px;padding:8px 0;">불러오는 중...</div>';
  try {
    var res = await db.from('board_comments').select('id,nickname,content,created_at').eq('post_id', postId).order('created_at', { ascending: true });
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) {
      clist.innerHTML = '<div style="color:#475569;font-size:13px;padding:8px 0;">첫 댓글을 남겨보세요!</div>';
      return;
    }
    clist.innerHTML = res.data.map(function(c) {
      return '<div class="board-comment" id="comment-' + c.id + '" data-postid="' + postId + '" data-raw="' + encodeURIComponent(c.content) + '">' +
        '<div class="board-comment-header">' +
          '<span class="board-comment-nick">' + escapeHtml(c.nickname) + '</span>' +
          '<span class="board-time">' + formatDate(c.created_at) + '</span>' +
          '<span style="margin-left:auto;display:flex;gap:4px;">' +
            '<button onclick="startEdit(' + c.id + ')" class="comment-action-btn">수정</button>' +
            '<button onclick="startDelete(' + c.id + ')" class="comment-action-btn del">삭제</button>' +
          '</span>' +
        '</div>' +
        '<div class="board-comment-content" id="cc-' + c.id + '">' + escapeHtml(c.content) + '</div>' +
        '<div id="comment-action-' + c.id + '"></div>' +
      '</div>';
    }).join('');
  } catch(e) {
    clist.innerHTML = '<div style="color:#f87171;font-size:13px;">오류: ' + escapeHtml(e.message) + '</div>';
  }
}

// ── 댓글 수정 (인라인) ───────────────────────────────────────────────────────
function startEdit(commentId) {
  var commentEl = document.getElementById('comment-' + commentId);
  var postId = commentEl.dataset.postid;
  var rawContent = decodeURIComponent(commentEl.dataset.raw);
  var actionDiv = document.getElementById('comment-action-' + commentId);

  // 이미 다른 수정/삭제 폼 닫기
  document.querySelectorAll('.inline-action-form').forEach(function(f) { f.remove(); });
  document.querySelectorAll('.board-comment-content').forEach(function(el) { el.style.display = ''; });

  // 원본 내용 숨기고 수정폼 표시
  document.getElementById('cc-' + commentId).style.display = 'none';
  actionDiv.innerHTML =
    '<div class="inline-action-form" style="margin-top:8px;">' +
      '<textarea id="edit-txt-' + commentId + '" class="board-contenteditable" style="resize:none;height:80px;width:100%;margin-bottom:6px;" maxlength="200">' + escapeHtml(rawContent) + '</textarea>' +
      '<input type="password" id="edit-pw-' + commentId + '" class="board-input" placeholder="비밀번호 확인" style="margin-bottom:8px;" />' +
      '<div style="display:flex;gap:8px;">' +
        '<button onclick="confirmEdit(' + commentId + ',' + postId + ')" class="board-submit" style="flex:1;padding:7px;">저장</button>' +
        '<button onclick="cancelAction(' + commentId + ')" class="comment-cancel-btn" style="flex:1;">취소</button>' +
      '</div>' +
    '</div>';
}

async function confirmEdit(commentId, postId) {
  var txt = document.getElementById('edit-txt-' + commentId).value.trim();
  var pw  = document.getElementById('edit-pw-' + commentId).value.trim();
  if (!txt) { showToast('내용을 입력해주세요', 'error'); return; }
  if (txt.length > 200) { showToast('200자 이하로 입력해주세요', 'error'); return; }
  if (!pw)  { showToast('비밀번호를 입력해주세요', 'error'); return; }
  try {
    var res = await db.from('board_comments').update({ content: txt }).eq('id', commentId).eq('password', pw).select();
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) { showToast('비밀번호가 틀렸습니다', 'error'); return; }
    showToast('댓글이 수정됐습니다', 'success');
    await loadComments(postId);
  } catch(e) {
    showToast('오류: ' + e.message, 'error');
  }
}

// ── 댓글 삭제 (인라인) ───────────────────────────────────────────────────────
function startDelete(commentId) {
  var commentEl = document.getElementById('comment-' + commentId);
  var postId = commentEl.dataset.postid;
  var actionDiv = document.getElementById('comment-action-' + commentId);

  document.querySelectorAll('.inline-action-form').forEach(function(f) { f.remove(); });
  document.querySelectorAll('.board-comment-content').forEach(function(el) { el.style.display = ''; });

  actionDiv.innerHTML =
    '<div class="inline-action-form" style="margin-top:8px;">' +
      '<input type="password" id="del-pw-' + commentId + '" class="board-input" placeholder="비밀번호 입력 후 삭제" style="margin-bottom:8px;" />' +
      '<div style="display:flex;gap:8px;">' +
        '<button onclick="confirmDelete(' + commentId + ',' + postId + ')" class="board-submit" style="flex:1;padding:7px;background:#3b1219;border-color:#7f1d1d;color:#fca5a5;">삭제 확인</button>' +
        '<button onclick="cancelAction(' + commentId + ')" class="comment-cancel-btn" style="flex:1;">취소</button>' +
      '</div>' +
    '</div>';
}

var ADMIN_PW = '0618';

async function confirmDelete(commentId, postId) {
  var pw = document.getElementById('del-pw-' + commentId).value.trim();
  if (!pw) { showToast('비밀번호를 입력해주세요', 'error'); return; }
  try {
    var query = db.from('board_comments').delete().eq('id', commentId);
    // 관리자 비밀번호면 password 조건 없이 삭제
    if (pw !== ADMIN_PW) query = query.eq('password', pw);
    var res = await query.select();
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) { showToast('비밀번호가 틀렸습니다', 'error'); return; }
    showToast('댓글이 삭제됐습니다', 'success');
    await loadComments(postId);
    var countRes = await db.from('board_comments').select('count').eq('post_id', postId);
    if (countRes.data && countRes.data[0]) {
      var btn = document.querySelector('#bcard-' + postId + ' .board-comment-btn');
      if (btn) btn.textContent = '💬 댓글 ' + countRes.data[0].count;
    }
  } catch(e) {
    showToast('오류: ' + e.message, 'error');
  }
}

function cancelAction(commentId) {
  var actionDiv = document.getElementById('comment-action-' + commentId);
  actionDiv.innerHTML = '';
  var contentEl = document.getElementById('cc-' + commentId);
  if (contentEl) contentEl.style.display = '';
}

// ── 댓글 등록 ────────────────────────────────────────────────────────────────
async function submitComment(postId) {
  var now = Date.now();
  if (now - lastCommentTime < COMMENT_COOLDOWN) {
    var wait = Math.ceil((COMMENT_COOLDOWN - (now - lastCommentTime)) / 1000);
    showToast(wait + '초 후에 댓글을 달 수 있어요', 'info'); return;
  }
  var nick = document.getElementById('cnick-' + postId).value.trim();
  var pw   = document.getElementById('cpw-' + postId).value.trim();
  var txtEl = document.getElementById('ctxt-' + postId);
  var txt  = txtEl ? txtEl.value.trim() : '';
  if (!nick)         { showToast('닉네임을 입력해주세요', 'error'); return; }
  if (nick.length > 20) { showToast('닉네임은 20자 이하로 입력해주세요', 'error'); return; }
  if (!pw)           { showToast('비밀번호를 입력해주세요', 'error'); return; }
  if (!txt)          { showToast('댓글 내용을 입력해주세요', 'error'); return; }
  if (txt.length > 200) { showToast('댓글은 200자 이하로 입력해주세요', 'error'); return; }
  try {
    var res = await db.from('board_comments').insert({ post_id: postId, nickname: nick, content: txt, password: pw });
    if (res.error) throw res.error;
    lastCommentTime = Date.now();
    if (txtEl) txtEl.value = '';
    document.getElementById('cpw-' + postId).value = '';
    showToast('댓글이 등록됐습니다', 'success');
    await loadComments(postId);
    var countRes = await db.from('board_comments').select('count').eq('post_id', postId);
    if (countRes.data && countRes.data[0]) {
      var btn = document.querySelector('#bcard-' + postId + ' .board-comment-btn');
      if (btn) btn.textContent = '💬 댓글 ' + countRes.data[0].count;
    }
  } catch(e) {
    showToast('오류: ' + e.message, 'error');
  }
}

// ── 게시글 등록 ──────────────────────────────────────────────────────────────
async function submitPost() {
  var now = Date.now();
  if (now - lastPostTime < POST_COOLDOWN) {
    var wait = Math.ceil((POST_COOLDOWN - (now - lastPostTime)) / 1000);
    showToast(wait + '초 후에 작성할 수 있어요', 'info'); return;
  }
  var nickname = document.getElementById('nickname').value.trim();
  var contentEl = document.getElementById('boardContent');
  var content  = contentEl ? contentEl.value.trim() : '';
  if (!nickname)          { showToast('닉네임을 입력해주세요', 'error'); return; }
  if (nickname.length > 20) { showToast('닉네임은 20자 이하로 입력해주세요', 'error'); return; }
  if (!content)           { showToast('내용을 입력해주세요', 'error'); return; }
  if (content.length > 300) { showToast('내용은 300자 이하로 입력해주세요', 'error'); return; }
  var btn = document.querySelector('.board-form .board-submit');
  btn.disabled = true; btn.textContent = '등록 중...';
  try {
    var res = await db.from('board_posts').insert({ nickname: nickname, content: content, likes: 0 });
    if (res.error) throw res.error;
    lastPostTime = Date.now();
    contentEl.value = '';
    document.getElementById('charCount').textContent = '0 / 300';
    showToast('게시글이 등록됐습니다', 'success');
    await loadBoard();
  } catch(e) {
    showToast('오류: ' + e.message, 'error');
  }
  btn.disabled = false; btn.textContent = '등록';
}

// ── 좋아요 (중복 방지) ────────────────────────────────────────────────────────
// ── 게시판 공유 (앵커 링크) ───────────────────────────────────────────────────
async function shareBoardPost(id) {
  var url = location.href.split('?')[0].split('#')[0] + '#bcard-' + id;
  if (navigator.share) {
    try { await navigator.share({ title: '겁쟁이리서치 게시판', url: url }); return; } catch(e) { if (e.name === 'AbortError') return; }
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(function() { showToast('링크가 복사됐습니다 🔗', 'success'); });
  } else {
    var el = document.createElement('textarea');
    el.value = url; el.style.cssText = 'position:fixed;opacity:0;';
    document.body.appendChild(el); el.select(); document.execCommand('copy'); document.body.removeChild(el);
    showToast('링크가 복사됐습니다 🔗', 'success');
  }
}

async function likePost(id) {
  var key = 'liked_' + id;
  if (localStorage.getItem(key)) {
    showToast('이미 좋아요를 눌렀어요 ❤️', 'info'); return;
  }
  var post = boardPosts.find(function(p) { return p.id === id; });
  if (!post) return;
  var newLikes = (post.likes || 0) + 1;
  post.likes = newLikes;
  var btn = document.querySelector('#bcard-' + id + ' .board-like');
  if (btn) { btn.textContent = '❤️ ' + newLikes; btn.classList.add('liked'); }
  localStorage.setItem(key, '1');
  await db.from('board_posts').update({ likes: newLikes }).eq('id', id);
}

loadBoard();
