#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_docx.py - DOCX 파일을 겁쟁이리서치 탭에 업로드

사용법:
  python upload_docx.py <docx파일경로>

예시:
  python upload_docx.py "C:\\Users\\asdf\\Documents\\애플분석.docx"
"""

import sys
import os
import io
import uuid

# Windows 콘솔 UTF-8 출력 설정
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from docx import Document
from docx.oxml.ns import qn
from supabase import create_client

# ── Supabase 설정 ──────────────────────────────────────────────────────────────
SUPABASE_URL = "https://miyrssfrjvhwswjylahw.supabase.co"
SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ."
    "rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts"
)
BUCKET_NAME = "post-images"

# ── 탭 선택 ────────────────────────────────────────────────────────────────────
TAB_OPTIONS = {
    "1": "🇺🇸 미국주식",
    "2": "🇰🇷 국내주식",
    "3": "🪙 암호화폐",
}

# ── 이미지 content-type → 확장자 ──────────────────────────────────────────────
EXT_MAP = {
    "image/png":  "png",
    "image/jpeg": "jpg",
    "image/jpg":  "jpg",
    "image/gif":  "gif",
    "image/webp": "webp",
    "image/bmp":  "bmp",
}

# ── Word 제목 스타일 → HTML 태그 ───────────────────────────────────────────────
HEADING_MAP = {
    "heading1": "h2", "heading2": "h3", "heading3": "h4",
    "heading 1": "h2", "heading 2": "h3", "heading 3": "h4",
    "제목1": "h2", "제목2": "h3", "제목3": "h4",
    "제목 1": "h2", "제목 2": "h3", "제목 3": "h4",
}


def upload_image(supabase, image_bytes: bytes, content_type: str) -> str:
    """이미지를 Supabase Storage에 업로드하고 public URL 반환"""
    ext = EXT_MAP.get(content_type, "png")
    filename = f"{uuid.uuid4()}.{ext}"
    supabase.storage.from_(BUCKET_NAME).upload(
        filename,
        image_bytes,
        file_options={"content-type": content_type},
    )
    return supabase.storage.from_(BUCKET_NAME).get_public_url(filename)


def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def process_run(run_xml, image_rels, supabase) -> str:
    """w:r 하나를 처리 — 텍스트(볼드/이탤릭) 또는 이미지 반환"""
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"

    # 이미지 체크 (w:drawing 안의 a:blip)
    blip = run_xml.find(f".//{{{A}}}blip")
    if blip is not None:
        r_embed = blip.get(f"{{{R}}}embed")
        if r_embed and r_embed in image_rels:
            rel = image_rels[r_embed]
            try:
                img_bytes = rel.target_part.blob
                ct = rel.target_part.content_type
                url = upload_image(supabase, img_bytes, ct)
                print(f"    [이미지] {url.split('/')[-1]}")
                return f'<img src="{url}" style="max-width:100%;margin:10px 0;border-radius:4px;" />'
            except Exception as e:
                print(f"    [경고] 이미지 업로드 실패: {e}")
                return ""

    # 일반 텍스트
    texts = [t.text or "" for t in run_xml.findall(f"{{{W}}}t")]
    text = "".join(texts)
    if not text:
        return ""

    text = html_escape(text)

    # rPr에서 볼드/이탤릭 확인
    rpr = run_xml.find(f"{{{W}}}rPr")
    if rpr is not None:
        # w:b 또는 w:bCs가 있고 w:b val="0"이 아닐 때 볼드
        b_el = rpr.find(f"{{{W}}}b")
        if b_el is not None and b_el.get(f"{{{W}}}val") != "0":
            text = f"<strong>{text}</strong>"
        i_el = rpr.find(f"{{{W}}}i")
        if i_el is not None and i_el.get(f"{{{W}}}val") != "0":
            text = f"<em>{text}</em>"

    return text


def process_paragraph(para_xml, image_rels, supabase) -> str:
    """w:p 하나를 HTML로 변환"""
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    # 스타일 확인 (제목 여부)
    tag = "p"
    ppr = para_xml.find(f"{{{W}}}pPr")
    if ppr is not None:
        pstyle = ppr.find(f"{{{W}}}pStyle")
        if pstyle is not None:
            style_val = pstyle.get(f"{{{W}}}val", "").lower()
            if style_val in HEADING_MAP:
                tag = HEADING_MAP[style_val]
            elif style_val.startswith("heading"):
                # 'heading4' 같이 숫자가 붙은 경우
                try:
                    lvl = int(style_val.replace("heading", "").strip())
                    tag = f"h{min(lvl + 1, 6)}"
                except ValueError:
                    pass

    # runs와 hyperlink 처리
    parts = []
    for child in para_xml:
        local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local == "r":
            parts.append(process_run(child, image_rels, supabase))
        elif local == "hyperlink":
            for r in child.findall(f"{{{W}}}r"):
                parts.append(process_run(r, image_rels, supabase))
        elif local == "br":
            parts.append("<br>")

    content = "".join(parts)
    if not content.strip():
        return ""

    # 수평선 문자(─, ━, ─ 등)로만 이루어진 단락은 <hr>로 변환
    stripped = content.replace("&amp;", "").replace("&lt;", "").replace("&gt;", "")
    stripped = stripped.replace("<strong>", "").replace("</strong>", "")
    stripped = stripped.replace("<em>", "").replace("</em>", "")
    if stripped and all(c in "─━―─—–\u2500\u2501\u2014\u2013 " for c in stripped):
        return "<hr>"

    return f"<{tag}>{content}</{tag}>"


def process_table(table_xml) -> str:
    """w:tbl 하나를 HTML table로 변환"""
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    rows_html = []

    for tr in table_xml.findall(f"{{{W}}}tr"):
        cells_html = []
        is_header_row = len(rows_html) == 0  # 첫 행은 헤더로 처리
        for tc in tr.findall(f"{{{W}}}tc"):
            # 셀 안의 텍스트 전부 합치기
            cell_text = ""
            for r in tc.findall(f".//{{{W}}}r"):
                for t in r.findall(f"{{{W}}}t"):
                    cell_text += t.text or ""
            cell_content = html_escape(cell_text)
            cell_tag = "th" if is_header_row else "td"

            # colspan 체크 (w:gridSpan)
            tc_pr = tc.find(f"{{{W}}}tcPr")
            colspan = ""
            if tc_pr is not None:
                gs = tc_pr.find(f"{{{W}}}gridSpan")
                if gs is not None:
                    val = gs.get(f"{{{W}}}val", "1")
                    if val != "1":
                        colspan = f' colspan="{val}"'

            cells_html.append(f"<{cell_tag}{colspan}>{cell_content}</{cell_tag}>")

        rows_html.append("<tr>" + "".join(cells_html) + "</tr>")

    return '<div class="docx-table-wrap"><table class="docx-table"><tbody>' + "".join(rows_html) + "</tbody></table></div>"


def docx_to_html(doc_path: str, supabase) -> str:
    """DOCX 파일 전체를 HTML 문자열로 변환"""
    doc = Document(doc_path)

    # 이미지 관계 수집
    image_rels = {}
    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_rels[rel.rId] = rel

    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    html_parts = []

    for child in doc.element.body:
        local = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if local == "p":
            h = process_paragraph(child, image_rels, supabase)
            if h:
                html_parts.append(h)
        elif local == "tbl":
            html_parts.append(process_table(child))

    return "\n".join(html_parts)


def main():
    print("=" * 50)
    print("  겁쟁이리서치 DOCX 업로더")
    print("=" * 50)

    # ── DOCX 파일 경로 ──────────────────────────────
    if len(sys.argv) >= 2:
        doc_path = sys.argv[1].strip('"').strip("'")
    else:
        doc_path = input("[파일] DOCX 경로: ").strip().strip('"').strip("'")

    if not os.path.exists(doc_path):
        print(f"[오류] 파일을 찾을 수 없음: {doc_path}")
        sys.exit(1)

    print(f"[확인] {os.path.basename(doc_path)}")

    # ── 탭 선택 ─────────────────────────────────────
    print()
    print("[탭 선택] 어디에 올릴까요?")
    for k, v in TAB_OPTIONS.items():
        print(f"  {k}. {v}")

    choice = input("번호: ").strip()
    if choice not in TAB_OPTIONS:
        print("[오류] 잘못된 번호")
        sys.exit(1)

    category = TAB_OPTIONS[choice]

    # ── 제목 입력 ────────────────────────────────────
    print()
    title = input("[제목] : ").strip()
    if not title:
        print("[오류] 제목을 입력해야 합니다")
        sys.exit(1)

    # ── 변환 & 업로드 ─────────────────────────────────
    print()
    print("[변환 중] DOCX 변환 + 이미지 업로드...")
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    try:
        html_content = docx_to_html(doc_path, supabase)
    except Exception as e:
        print(f"[오류] 변환 실패: {e}")
        sys.exit(1)

    print(f"[업로드] '{category}' 탭에 게시 중...")
    try:
        result = supabase.table("posts").insert({
            "category": category,
            "title": title,
            "content": html_content,
            "views": 0,
        }).execute()

        if result.data:
            post_id = result.data[0]["id"]
            print(f"[완료] 업로드 성공! (ID: {post_id})")
            print(f"  탭: {category}")
            print(f"  제목: {title}")
        else:
            print("[오류] 업로드 실패 (응답 데이터 없음)")
    except Exception as e:
        print(f"[오류] 업로드 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
