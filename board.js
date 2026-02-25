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

function previewGif(input, previewId, nameId) {
  var file = input.files[0];
  if (!file) return;
  var preview = document.getElementById(previewId);
  var nameEl = document.getElementById(nameId);
  var reader = new FileReader();
  reader.onload = function(e) {
    preview.src = e.target.result;
    preview.style.display = 'block';
  };
  reader.readAsDataURL(file);
  if (nameEl) nameEl.textContent = file.name;
}

async function uploadGif(file) {
  var ext = file.name.split('.').pop() || 'gif';
  var fileName = Date.now() + '-' + Math.random().toString(36).slice(2) + '.' + ext;
  var res = await db.storage.from('board-gifs').upload(fileName, file, { contentType: file.type });
  if (res.error) throw res.error;
  return db.storage.from('board-gifs').getPublicUrl(fileName).data.publicUrl;
}

function gifUrlToImg(url) {
  if (!url) return '';
  return '<img src="' + escapeHtml(url) + '" class="board-gif-img" onerror="this.style.display=\'none\'" />';
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
        (p.gif_url ? gifUrlToImg(p.gif_url) : '') +
        '<div class="board-card-footer">' +
          '<button class="board-like" onclick="likePost(' + p.id + ')">❤️ ' + (p.likes || 0) + '</button>' +
          '<button class="board-comment-btn" onclick="toggleComments(' + p.id + ')">💬 댓글 ' + commentCount + '</button>' +
        '</div>' +
        '<div class="board-comments-wrap" id="comments-' + p.id + '" style="display:none;">' +
          '<div class="board-comments-list" id="clist-' + p.id + '"></div>' +
          '<div class="board-comment-form">' +
            '<input type="text" class="board-input" id="cnick-' + p.id + '" placeholder="닉네임" maxlength="20" style="margin-bottom:6px;" />' +
            '<div style="display:flex;gap:8px;align-items:center;">' +
              '<input type="text" class="board-input" id="ctxt-' + p.id + '" placeholder="댓글을 입력하세요" maxlength="200" style="margin-bottom:0;flex:1;" />' +
              '<button class="board-gif-btn" onclick="document.getElementById(\'cgiffile-' + p.id + '\').click()">🎬</button>' +
              '<button class="board-submit" style="padding:8px 14px;white-space:nowrap;" onclick="submitComment(' + p.id + ')">등록</button>' +
            '</div>' +
            '<input type="file" id="cgiffile-' + p.id + '" accept="image/gif,image/*" style="display:none;" onchange="previewGif(this,\'cgifpreview-' + p.id + '\',null)" />' +
            '<img id="cgifpreview-' + p.id + '" class="board-gif-preview" src="" style="display:none;margin-top:6px;" />' +
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
    var res = await db.from('board_comments').select('*').eq('post_id', postId).order('created_at', { ascending: true });
    if (res.error) throw res.error;
    if (!res.data || !res.data.length) {
      clist.innerHTML = '<div style="color:#475569;font-size:13px;padding:8px 0;">첫 댓글을 남겨보세요!</div>';
      return;
    }
    clist.innerHTML = res.data.map(function(c) {
      return '<div class="board-comment">' +
        '<div class="board-comment-header">' +
          '<span class="board-comment-nick">' + escapeHtml(c.nickname) + '</span>' +
          '<span class="board-time">' + formatDate(c.created_at) + '</span>' +
        '</div>' +
        '<div class="board-comment-content">' + escapeHtml(c.content) + '</div>' +
        (c.gif_url ? gifUrlToImg(c.gif_url) : '') +
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
  var txt = document.getElementById('ctxt-' + postId).value.trim();
  var gifFileEl = document.getElementById('cgiffile-' + postId);
  var gifFile = gifFileEl ? gifFileEl.files[0] : null;
  if (!nick) { alert('닉네임을 입력해주세요'); return; }
  if (nick.length > 20) { alert('닉네임은 20자 이하로 입력해주세요'); return; }
  if (!txt && !gifFile) { alert('댓글 내용을 입력해주세요'); return; }
  if (txt.length > 200) { alert('댓글은 200자 이하로 입력해주세요'); return; }
  try {
    var gifUrl = '';
    if (gifFile) gifUrl = await uploadGif(gifFile);
    var row = { post_id: postId, nickname: nick, content: txt };
    if (gifUrl) row.gif_url = gifUrl;
    var res = await db.from('board_comments').insert(row);
    if (res.error) throw res.error;
    lastCommentTime = Date.now();
    document.getElementById('ctxt-' + postId).value = '';
    if (gifFileEl) { gifFileEl.value = ''; }
    var preview = document.getElementById('cgifpreview-' + postId);
    if (preview) { preview.style.display = 'none'; preview.src = ''; }
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
  var content = document.getElementById('boardContent').value.trim();
  var gifFile = document.getElementById('postGifFile') ? document.getElementById('postGifFile').files[0] : null;
  if (!nickname) { alert('닉네임을 입력해주세요'); return; }
  if (nickname.length > 20) { alert('닉네임은 20자 이하로 입력해주세요'); return; }
  if (!content && !gifFile) { alert('내용을 입력해주세요'); return; }
  if (content.length > 300) { alert('내용은 300자 이하로 입력해주세요'); return; }
  var btn = document.querySelector('.board-form .board-submit');
  btn.disabled = true;
  btn.textContent = '등록 중...';
  try {
    var gifUrl = '';
    if (gifFile) gifUrl = await uploadGif(gifFile);
    var row = { nickname: nickname, content: content, likes: 0 };
    if (gifUrl) row.gif_url = gifUrl;
    var res = await db.from('board_posts').insert(row);
    if (res.error) throw res.error;
    lastPostTime = Date.now();
    document.getElementById('boardContent').value = '';
    document.getElementById('charCount').textContent = '0 / 300';
    document.getElementById('postGifFile').value = '';
    document.getElementById('postGifPreview').style.display = 'none';
    document.getElementById('postGifName').textContent = '';
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

document.getElementById('boardContent').addEventListener('input', function() {
  document.getElementById('charCount').textContent = this.value.length + ' / 300';
});

loadBoard();
