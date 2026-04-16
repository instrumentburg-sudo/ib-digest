#!/usr/bin/env python3
"""Render AI-дайджест: MD-текст → HTML страница + обновление digest/index.html."""
import re
import sys
import json
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIGEST_DIR = ROOT / "digest"
EKB = timezone(timedelta(hours=5))


def md_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(
        r"(https?://[^\s<>()\"]+)",
        lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    return text


def md_to_html(md: str) -> str:
    """Простой рендер — для нашего формата дайджеста достаточно."""
    out = []
    for line in md.splitlines():
        s = line.rstrip()
        if not s:
            out.append("")
            continue
        if s.startswith("🔧 ") or s.startswith("🤖 ") or s.startswith("📡 ") or s.startswith("🔍 "):
            out.append(f"<h2>{md_inline(s)}</h2>")
        elif re.match(r"^\d+\.\s", s):
            out.append(f"<h3>{md_inline(s)}</h3>")
        elif s.startswith("• "):
            out.append(f'<p style="margin-left:12px">• {md_inline(s[2:])}</p>')
        elif s.startswith("  → "):
            out.append(f'<blockquote><strong>→ Нам:</strong> {md_inline(s[4:])}</blockquote>')
        elif s.startswith("👉 "):
            out.append(f'<blockquote><strong>👉</strong> {md_inline(s[2:])}</blockquote>')
        else:
            out.append(f"<p>{md_inline(s)}</p>")
    return "\n".join(out)


def build_page(date_str: str, md: str, title: str) -> str:
    body = md_to_html(md)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>📡 {html.escape(title)}</h1>
      <div class="meta"><a href="./" class="back">← все выпуски</a> · {date_str}</div>
    </header>
    {body}
    <footer>Сгенерировано автоматически · <a href="https://github.com/instrumentburg-sudo/ib-digest">source</a></footer>
  </div>
</body>
</html>
"""


def first_line_preview(md: str) -> str:
    """Найти первый информативный заголовок для превью."""
    for line in md.splitlines():
        s = line.strip()
        if s and not s.startswith("🔍") and len(s) > 5:
            return s[:90]
    return ""


def update_index(date_str: str, preview: str):
    """Добавить ссылку в digest/index.html. Новые — сверху."""
    idx = DIGEST_DIR / "index.html"
    content = idx.read_text()
    item = (
        f'      <li><a href="{date_str}.html">Дайджест {date_str}</a>'
        f'<span class="preview">{html.escape(preview)}</span>'
        f'<span class="date">{date_str}</span></li>\n'
    )
    # Не дублируем
    if f'href="{date_str}.html"' in content:
        content = re.sub(
            rf'      <li><a href="{date_str}\.html">.*?</li>\n',
            item,
            content,
            flags=re.DOTALL,
        )
    else:
        content = content.replace(
            "<!-- ITEMS_START -->\n",
            f"<!-- ITEMS_START -->\n{item}",
        )
    idx.write_text(content)


def main():
    if len(sys.argv) < 2:
        print("Usage: render-digest.py <input-md-file> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)
    md_path = Path(sys.argv[1])
    md = md_path.read_text()
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now(EKB).strftime("%Y-%m-%d")
    title = f"Дайджест {date_str}"
    page = build_page(date_str, md, title)
    out = DIGEST_DIR / f"{date_str}.html"
    out.write_text(page)
    update_index(date_str, first_line_preview(md))
    print(f"Wrote {out}")
    print(f"URL: https://instrumentburg-sudo.github.io/ib-digest/digest/{date_str}.html")


if __name__ == "__main__":
    main()
