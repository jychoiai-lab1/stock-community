// /post/:id 로 접근 시 동적 OG 태그 + 리다이렉트
const SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMjIxNDYsImV4cCI6MjA4NzU5ODE0Nn0.oBwDXc1x4II1M4NX5AcfXIt2MTx4L3m4e9mHwqo-ObA';
const SITE_URL = 'https://stock-community-woad.vercel.app';

function stripHtml(html) {
  return html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/&[^;]+;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
    .replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

module.exports = async (req, res) => {
  const id = parseInt(req.query.id) || 0;
  const redirectUrl = `${SITE_URL}/?post=${id}`;

  let title = '겁쟁이리서치';
  let description = '주식·경제 분석 리서치 커뮤니티. 매일 브리핑, 미국·국내주식, 암호화폐 분석.';
  let category = '';

  if (id) {
    try {
      const resp = await fetch(
        `${SUPABASE_URL}/rest/v1/posts?id=eq.${id}&select=title,content,category&limit=1`,
        { headers: { apikey: ANON_KEY, Authorization: `Bearer ${ANON_KEY}` } }
      );
      const data = await resp.json();
      if (data && data[0]) {
        const post = data[0];
        title = post.title || '겁쟁이리서치';
        category = post.category || '';
        const text = stripHtml(post.content || '')
          .replace(/⚠️.*?자본시장법 제57조/s, '')
          .replace(/본 콘텐츠는.*?있습니다\./s, '')
          .trim();
        description = text.slice(0, 120) + (text.length > 120 ? '...' : '');
      }
    } catch (e) { /* fallback to defaults */ }
  }

  const ogTitle = esc(title + ' | 겁쟁이리서치');
  const ogDesc = esc(description);
  const ogUrl = esc(`${SITE_URL}/post/${id}`);
  const ogImg = esc(`${SITE_URL}/og-image.svg`);

  const html = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>${ogTitle}</title>
<meta property="og:type" content="article">
<meta property="og:site_name" content="겁쟁이리서치">
<meta property="og:title" content="${ogTitle}">
<meta property="og:description" content="${ogDesc}">
<meta property="og:url" content="${ogUrl}">
<meta property="og:image" content="${ogImg}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${ogTitle}">
<meta name="twitter:description" content="${ogDesc}">
<meta name="twitter:image" content="${ogImg}">
<meta http-equiv="refresh" content="0;url=${esc(redirectUrl)}">
</head>
<body>
<script>location.replace(${JSON.stringify(redirectUrl)});</script>
<p>잠시 후 이동합니다... <a href="${esc(redirectUrl)}">여기를 클릭하세요</a></p>
</body>
</html>`;

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');
  res.status(200).send(html);
};
