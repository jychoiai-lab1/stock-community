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
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

function onPostInput() {
  var el = document.getElementById('boardContent');
  document.getElementById('charCount').textContent = el.value.length + ' / 300';
}

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
      return '<div class="board-card" id="bcard-' + p.id + '">' +
        '<div class="board-card-header">' +
          '<span class="board-nickname">' + escapeHtml(p.nickname) + '</span>' +
          '<span class="board-time">' + formatDate(p.created_at) + '</span>' +
        '</div>' +
        '<div class="board-card-content">' + escapeHtml(p.content) + '</div>' +
        '<div class="board-card-footer">' +
          '<button class="board-like" onclick="likePost(' + p.id + ')">❤️ ' + (p.likes || 0) + '</button>' +
          '<button class="board-comment-btn" onclick="toggleComments(' + p.id + ')">💬 댓글 ' + commentCount + '</button>' +
        '</div>' +
        '<div class="board-comments-wrap" id="comments-' + p.id + '" style="display:none;">' +
          '<div class="board-comments-list" id="clist-' + p.id + '"></div>' +
          '<div class="board-comment-form">' +
            '<input type="text" class="board-input" id="cnick-' + p.id + '" placeholder="닉네임" maxlength="20" style="margin-bottom:6px;" />' +
            '<input type="password" class="board-input" id="cpw-' + p.id + '" placeholder="비밀번호 (수정/삭제시 필요)" maxlength="20" style="margin-bottom:6px;" />' +
            '<textarea class="board-contenteditable" id="ctxt-' + p.id + '" placeholder="댓글을 입력하세요" maxlength="200" style="resize:none;height:70px;"></textarea>' +
            '<button class="board-submit" style="margin-top:8px;width:100%;" onclick="submitComment(' + p.id + ')">댓글 등록</button>' +
          '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">오류: ' + e.message + '</div></div>';
  }
}

async function toggleComments(postId) {
  var wrap = document.getElementById('comments-' + postId);
  if (wrap.style.display === 'none') {
    wrap.style.display = 'block';
    await loadComments(postId);
  } else {
    wrap.style.display = 'none';
  }
}

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
      return '<div class="board-comment" id="comment-' + c.id + '">' +
        '<div class="board-comment-header">' +
          '<span class="board-comment-nick">' + escapeHtml(c.nickname) + '</span>' +
          '<span class="board-time">' + formatDate(c.created_at) + '</span>' +
          '<span style="margin-left:auto;">' +
            '<button onclick="editComment(' + c.id + ',' + postId + ')" style="background:none;border:none;color:#94a3b8;font-size:12px;cursor:pointer;padding:0 4px;">수정</button>' +
            '<button onclick="deleteComment(' + c.id + ',' + postId + ')" style="background:none;border:none;color:#94a3b8;font-size:12px;cursor:pointer;padding:0 4px;">삭제</button>' +
          '</span>' +
        '</div>' +
        '<div class="board-comment-content" id="cc-' + c.id + '">' + escapeHtml(c.content) + '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    clist.innerHTML = '<div style="color:#f87171;font-size:13px;">오류: ' + e.message + '</div>';
  }
}

async function submitComment(postId) {
  var now = Date.now();
  if (now - lastCommentTime < COMMENT_COOLDOWN) {
    var wait = Math.ceil((COMMENT_COOLDOWN - (now - lastCommentTime)) / 1000);
    alert(wait + '초 후에 다시 댓글을 달 수 있어요'); return;
  }
  var nick = document.getElementById('cnick-' + postId).value.trim();
  var pw = document.getElementById('cpw-' + postId).value.trim();
  var txtEl = document.getElementById('ctxt-' + postId);
  var txt = txtEl ? txtEl.value.trim() : '';
  if (!nick) { alert('닉네임을 입력해주세요'); return; }
  if (nick.length > 20) { alert('닉네임은 20자 이하로 입력해주세요'); return; }
  if (!pw) { alert('비밀번호를 입력해주세요'); return; }
  if (!txt) { alert('댓글 내용을 입력해주세요'); return; }
  if (txt.length > 200) { alert('댓글은 200자 이하로 입력해주세요'); return; }
  try {
    var res = await db.from('board_comments').insert({ post_id: postId, nickname: nick, content: txt, password: pw });
    if (res.error) throw res.error;
    lastCommentTime = Date.now();
    if (txtEl) txtEl.value = '';
    document.getElementById('cpw-' + postId).value = '';
    await loadComments(postId);
    var countRes = await db.from('board_comments').select('count').eq('post_id', postId);
    if (countRes.data && countRes.data[0]) {
      var btn = document.querySelector('#bcard-' + postId + ' .board-comment-btn');
      if (btn) btn.textContent = '💬 댓글 ' + countRes.data[0].count;
    }
  } catch(e) {
    alert('오류: ' + e.message);
  }
}

async function editComment(commentId, postId) {
  var pw = prompt('비밀번호를 입력하세요');
  if (pw === null) return;
  var contentEl = document.getElementById('cc-' + commentId);
  var current = contentEl ? contentEl.textContent : '';
  var newContent = prompt('수정할 내용:', current);
  if (newContent === null) return;
  newContent = newContent.trim();
  if (!newContent) { alert('내용을 입력해주세요'); return; }
  if (newContent.length > 200) { alert('200자 이하로 입력해주세요'); return; }
  try {
    var res = await db.from('board_comments').update({ content: newContent }).eq('id', commentId).eq('password', pw).select();
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) { alert('비밀번호가 틀렸습니다'); return; }
    await loadComments(postId);
  } catch(e) {
    alert('오류: ' + e.message);
  }
}

async function deleteComment(commentId, postId) {
  var pw = prompt('비밀번호를 입력하세요');
  if (pw === null) return;
  if (!confirm('댓글을 삭제하시겠습니까?')) return;
  try {
    var res = await db.from('board_comments').delete().eq('id', commentId).eq('password', pw).select();
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) { alert('비밀번호가 틀렸습니다'); return; }
    await loadComments(postId);
    var countRes = await db.from('board_comments').select('count').eq('post_id', postId);
    if (countRes.data && countRes.data[0]) {
      var btn = document.querySelector('#bcard-' + postId + ' .board-comment-btn');
      if (btn) btn.textContent = '💬 댓글 ' + countRes.data[0].count;
    }
  } catch(e) {
    alert('오류: ' + e.message);
  }
}

async function submitPost() {
  var now = Date.now();
  if (now - lastPostTime < POST_COOLDOWN) {
    var wait = Math.ceil((POST_COOLDOWN - (now - lastPostTime)) / 1000);
    alert(wait + '초 후에 다시 작성할 수 있어요'); return;
  }
  var nickname = document.getElementById('nickname').value.trim();
  var contentEl = document.getElementById('boardContent');
  var content = contentEl ? contentEl.value.trim() : '';
  if (!nickname) { alert('닉네임을 입력해주세요'); return; }
  if (nickname.length > 20) { alert('닉네임은 20자 이하로 입력해주세요'); return; }
  if (!content) { alert('내용을 입력해주세요'); return; }
  if (content.length > 300) { alert('내용은 300자 이하로 입력해주세요'); return; }
  var btn = document.querySelector('.board-form .board-submit');
  btn.disabled = true;
  btn.textContent = '등록 중...';
  try {
    var res = await db.from('board_posts').insert({ nickname: nickname, content: content, likes: 0 });
    if (res.error) throw res.error;
    lastPostTime = Date.now();
    contentEl.value = '';
    document.getElementById('charCount').textContent = '0 / 300';
    await loadBoard();
  } catch(e) {
    alert('오류: ' + e.message);
  }
  btn.disabled = false;
  btn.textContent = '등록';
}

async function likePost(id) {
  var post = boardPosts.find(function(p) { return p.id === id; });
  if (!post) return;
  var newLikes = (post.likes || 0) + 1;
  post.likes = newLikes;
  var btn = document.querySelector('#bcard-' + id + ' .board-like');
  if (btn) btn.textContent = '❤️ ' + newLikes;
  await db.from('board_posts').update({ likes: newLikes }).eq('id', id);
}

loadBoard();
