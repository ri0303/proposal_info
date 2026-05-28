#!/usr/bin/env python3
"""Convert a proposal daily-report Markdown file to a styled HTML file.

Usage:
    python3 scripts/md_to_html.py reports/YYYY-MM-DD.md
    # -> reports/YYYY-MM-DD.html
"""

import re
import sys
from pathlib import Path

# ── CSS ────────────────────────────────────────────────────────────────────

CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: "Hiragino Sans", "Yu Gothic", sans-serif;
  font-size: 14px; line-height: 1.7; color: #222; background: #f5f5f5;
}
.page {
  max-width: 1100px; margin: 32px auto; background: #fff;
  border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,.08); overflow: hidden;
}
.header {
  background: linear-gradient(135deg, #1a3a5c 0%, #2d6a9f 100%);
  color: #fff; padding: 28px 36px 22px;
}
.header h1 { font-size: 20px; font-weight: 700; letter-spacing: .02em; }
.header .meta { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 10px; font-size: 13px; opacity: .85; }
.badge {
  display: inline-block; background: rgba(255,255,255,.2);
  border: 1px solid rgba(255,255,255,.4); border-radius: 4px;
  padding: 2px 10px; font-size: 12px;
}
.summary-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 16px; padding: 24px 36px; background: #f0f4f8;
  border-bottom: 1px solid #dde3ea;
}
.card {
  background: #fff; border-radius: 6px; padding: 14px 18px;
  text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06);
}
.card .num { font-size: 28px; font-weight: 700; color: #2d6a9f; }
.card .label { font-size: 12px; color: #666; margin-top: 2px; }
.section { padding: 28px 36px; border-bottom: 1px solid #eee; }
.section:last-child { border-bottom: none; }
h2 {
  font-size: 16px; font-weight: 700; color: #1a3a5c;
  border-left: 4px solid #2d6a9f; padding-left: 10px; margin-bottom: 16px;
}
h3 { font-size: 14px; font-weight: 700; color: #2d6a9f; margin: 20px 0 8px; }
.table-wrap { overflow-x: auto; margin-bottom: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead tr { background: #1a3a5c; color: #fff; }
thead th { padding: 10px 12px; text-align: left; font-weight: 600; white-space: nowrap; }
tbody tr:nth-child(even) { background: #f8fafc; }
tbody tr:hover { background: #eaf2fb; }
tbody td { padding: 9px 12px; vertical-align: top; }
tbody td a, .spotlight a { color: #2d6a9f; text-decoration: none; }
tbody td a:hover, .spotlight a:hover { text-decoration: underline; }
.status-open   { display:inline-block; background:#e6f4ea; color:#2e7d32; border:1px solid #a5d6a7; border-radius:4px; padding:1px 8px; font-size:11px; white-space:nowrap; }
.status-check  { display:inline-block; background:#fff8e1; color:#f57f17; border:1px solid #ffe082; border-radius:4px; padding:1px 8px; font-size:11px; white-space:nowrap; }
.status-closed { display:inline-block; background:#fce4ec; color:#c62828; border:1px solid #ef9a9a; border-radius:4px; padding:1px 8px; font-size:11px; white-space:nowrap; }
.spotlight {
  border: 1px solid #c8dff4; border-radius: 6px; padding: 16px 20px;
  margin-bottom: 14px; background: #f4f9ff;
}
.spotlight .s-title { font-weight: 700; font-size: 14px; color: #1a3a5c; }
.spotlight .rank {
  display:inline-block; background:#2d6a9f; color:#fff; border-radius:50%;
  width:22px; height:22px; line-height:22px; text-align:center;
  font-size:12px; font-weight:700; margin-right:6px;
}
.spotlight dl { display:grid; grid-template-columns:90px 1fr; gap:4px 8px; margin-top:10px; font-size:13px; }
.spotlight dt { color:#555; font-weight:600; }
.trend-list { list-style:none; }
.trend-list li { padding:8px 0 8px 20px; border-bottom:1px dashed #ddd; position:relative; font-size:13px; }
.trend-list li:last-child { border-bottom:none; }
.trend-list li::before { content:"▶"; position:absolute; left:0; color:#2d6a9f; font-size:10px; top:10px; }
.trend-list li strong { color:#1a3a5c; }
.error-box { background:#fff8f8; border:1px solid #ffcdd2; border-radius:6px; padding:14px 18px; }
.error-box ul { padding-left:18px; font-size:13px; }
.error-box li { margin-bottom:6px; }
.error-box li strong { color:#c62828; }
.plain-list { padding-left: 18px; font-size: 13px; }
.plain-list li { margin-bottom: 4px; }
.footer { text-align:center; font-size:12px; color:#999; padding:16px; background:#f5f5f5; border-top:1px solid #eee; }
""".strip()

# ── Inline markdown helpers ────────────────────────────────────────────────

def inline(text: str) -> str:
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                  r'<a href="\2" target="_blank">\1</a>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text

# ── Deadline badge ─────────────────────────────────────────────────────────

def deadline_badge(text: str) -> str:
    t = text.strip()
    if '締切済' in t or '締切済み' in t:
        return f'<span class="status-closed">{t}</span>'
    if '要確認' in t or '不明' in t:
        return f'<span class="status-check">{t}</span>'
    if t and t != '-':
        return f'<span class="status-open">{t}</span>'
    return t

# ── Table parser ───────────────────────────────────────────────────────────

def parse_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        if re.match(r'^\|[-| :]+\|$', line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    if not rows:
        return ''
    html = ['<div class="table-wrap"><table>']
    html.append('<thead><tr>')
    for cell in rows[0]:
        html.append(f'<th>{inline(cell)}</th>')
    html.append('</tr></thead><tbody>')
    deadline_col = None
    headers = [h.strip() for h in rows[0]]
    if '締切日' in headers:
        deadline_col = headers.index('締切日')
    for row in rows[1:]:
        html.append('<tr>')
        for i, cell in enumerate(row):
            if i == deadline_col:
                html.append(f'<td>{deadline_badge(cell)}</td>')
            else:
                html.append(f'<td>{inline(cell)}</td>')
        html.append('</tr>')
    html.append('</tbody></table></div>')
    return '\n'.join(html)

# ── Section renderers ──────────────────────────────────────────────────────

def render_summary(lines: list[str], title: str) -> str:
    meta: dict[str, str] = {}
    count_val = '?'
    for line in lines:
        m = re.match(r'-\s*(.+?)[:：]\s*(.+)', line)
        if m:
            key, val = m.group(1).strip(), m.group(2).strip()
            meta[key] = val
            if '件数' in key or '収集件数' in key:
                nm = re.match(r'(\d+)', val)
                count_val = nm.group(1) if nm else val

    open_val   = '–'
    closed_val = '–'
    full_count = meta.get('収集件数', meta.get('件数', count_val))
    m_closed = re.search(r'締切済[みぃ]?[参考案件]*(\d+)件', full_count)
    if m_closed:
        closed_val = m_closed.group(1)
        total_m = re.match(r'(\d+)', full_count)
        if total_m:
            open_val = str(int(total_m.group(1)) - int(closed_val))

    cards_html = f"""
  <div class="summary-grid">
    <div class="card"><div class="num">{count_val}</div><div class="label">収集件数</div></div>
    <div class="card"><div class="num">{open_val}</div><div class="label">公募中（締切要確認含む）</div></div>
    <div class="card"><div class="num">{closed_val}</div><div class="label">締切済み（参考掲載）</div></div>
  </div>"""

    h1_m = re.search(r'(\d{4}-\d{2}-\d{2})[（(]([^）)]+)[）)]', title)
    if h1_m:
        date_badge  = h1_m.group(1)
        rest        = h1_m.group(2)
        parts       = [p.strip() for p in rest.split('/')]
    else:
        date_badge = meta.get('収集日', '')
        parts      = [meta.get('対象', '')]

    badges_html = f'<span class="badge">{date_badge}</span>\n'
    for p in parts:
        badges_html += f'      <span class="badge">{p}</span>\n'

    header_html = f"""  <div class="header">
    <h1>建築設計プロポーザル情報</h1>
    <div class="meta">
      {badges_html.strip()}
    </div>
  </div>"""

    return header_html + '\n' + cards_html

def render_proposals(lines: list[str]) -> str:
    html_parts: list[str] = []
    table_buf: list[str] = []

    def flush_table():
        if table_buf:
            html_parts.append(parse_table(table_buf))
            table_buf.clear()

    for line in lines:
        if line.startswith('### '):
            flush_table()
            html_parts.append(f'<h3>{inline(line[4:].strip())}</h3>')
        elif line.startswith('|'):
            table_buf.append(line)
        else:
            flush_table()
    flush_table()
    return '\n'.join(html_parts)

def render_spotlight(lines: list[str]) -> str:
    html_parts: list[str] = []
    in_card    = False
    rank       = 0
    card_title = ''
    dl_items: list[tuple[str, str]] = []

    def flush_card():
        nonlocal in_card
        if not in_card:
            return
        dl_html = '\n'.join(
            f'<dt>{k}</dt><dd>{inline(v)}</dd>' for k, v in dl_items
        )
        html_parts.append(
            f'<div class="spotlight">'
            f'<div><span class="rank">{rank}</span>'
            f'<span class="s-title">{inline(card_title)}</span></div>'
            f'<dl>{dl_html}</dl></div>'
        )
        dl_items.clear()
        in_card = False

    for line in lines:
        h3 = re.match(r'###\s+(\d+)[.．]\s+(.+)', line)
        if h3:
            flush_card()
            rank, card_title = int(h3.group(1)), h3.group(2).strip()
            in_card = True
            continue
        if in_card:
            m = re.match(r'-\s*\*\*(.+?)\*\*[：:]\s*(.+)', line)
            if m:
                dl_items.append((m.group(1).strip(), m.group(2).strip()))
            elif line.strip().startswith('- '):
                dl_items.append(('', line.strip()[2:]))

    flush_card()
    return '\n'.join(html_parts)

def render_trends(lines: list[str]) -> str:
    html_parts: list[str] = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append('</ul>')
            in_list = False

    for line in lines:
        if line.startswith('### '):
            close_list()
            html_parts.append(f'<h3>{inline(line[4:].strip())}</h3>')
        elif line.strip().startswith('- '):
            if not in_list:
                html_parts.append('<ul class="trend-list">')
                in_list = True
            html_parts.append(f'<li>{inline(line.strip()[2:])}</li>')
        else:
            close_list()

    close_list()
    return '\n'.join(html_parts)

def render_errors(lines: list[str]) -> str:
    items = []
    for line in lines:
        if line.strip().startswith('- '):
            items.append(f'<li>{inline(line.strip()[2:])}</li>')
    if not items:
        return ''
    return f'<div class="error-box"><ul>{"" .join(items)}</ul></div>'

def render_query_log(lines: list[str]) -> str:
    table_lines = [l for l in lines if l.startswith('|')]
    return parse_table(table_lines) if table_lines else ''

def render_generic(lines: list[str]) -> str:
    html_parts: list[str] = []
    table_buf: list[str] = []
    list_buf:  list[str] = []

    def flush_table():
        if table_buf:
            html_parts.append(parse_table(table_buf))
            table_buf.clear()

    def flush_list():
        if list_buf:
            items = ''.join(f'<li>{inline(t)}</li>' for t in list_buf)
            html_parts.append(f'<ul class="plain-list">{items}</ul>')
            list_buf.clear()

    for line in lines:
        if line.startswith('|'):
            flush_list(); table_buf.append(line)
        elif line.strip().startswith('- '):
            flush_table(); list_buf.append(line.strip()[2:])
        elif line.startswith('### '):
            flush_table(); flush_list()
            html_parts.append(f'<h3>{inline(line[4:].strip())}</h3>')
        else:
            flush_table(); flush_list()
            if line.strip():
                html_parts.append(f'<p>{inline(line.strip())}</p>')

    flush_table(); flush_list()
    return '\n'.join(html_parts)

# ── Main parser ────────────────────────────────────────────────────────────

def parse_sections(md: str) -> dict:
    sections: dict[str, list[str]] = {}
    current = '__pre__'
    sections[current] = []
    for line in md.splitlines():
        if line.startswith('## '):
            current = line[3:].strip()
            sections[current] = []
        elif line.startswith('# '):
            sections['__title__'] = [line[2:].strip()]
        elif line.strip() == '---':
            pass
        else:
            sections.setdefault(current, []).append(line)
    return sections

def build_html(md: str, date_str: str) -> str:
    sections = parse_sections(md)
    title = sections.get('__title__', ['建築設計プロポーザル情報'])[0]
    body_parts: list[str] = ['<div class="page">']
    body_parts.append(render_summary(sections.get('サマリー', []), title))

    section_order = ['案件一覧', '注目案件', '所見・動向', '検索クエリログ', 'エラー・注意事項']
    for sec in section_order:
        lines = sections.get(sec, [])
        if not any(l.strip() for l in lines):
            continue
        body_parts.append('  <div class="section">')
        body_parts.append(f'    <h2>{sec}</h2>')
        if sec == '案件一覧':
            body_parts.append(render_proposals(lines))
        elif sec == '注目案件':
            body_parts.append(render_spotlight(lines))
        elif sec == '所見・動向':
            body_parts.append(render_trends(lines))
        elif sec == 'エラー・注意事項':
            body_parts.append(render_errors(lines))
        elif sec == '検索クエリログ':
            body_parts.append(render_query_log(lines))
        else:
            body_parts.append(render_generic(lines))
        body_parts.append('  </div>')

    body_parts.append(f'  <div class="footer">Generated by proposal-scout-bot &nbsp;|&nbsp; {date_str}</div>')
    body_parts.append('</div>')

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
{''.join(body_parts)}
</body>
</html>"""

# ── Entry point ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/md_to_html.py reports/YYYY-MM-DD.md')
        sys.exit(1)
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f'Error: {md_path} not found')
        sys.exit(1)
    date_str  = md_path.stem
    html_path = md_path.with_suffix('.html')
    html_text = build_html(md_path.read_text(encoding='utf-8'), date_str)
    html_path.write_text(html_text, encoding='utf-8')
    print(f'Generated: {html_path}')

if __name__ == '__main__':
    main()
