#!/usr/bin/env python3
"""Render AI-дайджест: MD-текст → HTML страница + обновление digest/index.html."""
import re
import sys
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIGEST_DIR = ROOT / "digest"
EKB = timezone(timedelta(hours=5))

EMOJI_HEAD = re.compile(r"^[\U0001F300-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2300-\u23FF\u2B00-\u2BFF]")


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
    """Специализированный рендер под наш формат дайджеста."""
    out = []
    in_bullets = False

    def close_bullets():
        nonlocal in_bullets
        if in_bullets:
            out.append("</ul>")
            in_bullets = False

    for raw in md.splitlines():
        s = raw.rstrip()
        if not s:
            close_bullets()
            continue

        # Пропускаем верхнюю шапку "🔍 Утренний дайджест — <дата>" — она рендерится в page-header
        if s.startswith("🔍 Утренний дайджест") or s.startswith("🔍 Дайджест"):
            continue

        stripped = s.lstrip()

        # "→ Нам: ..." / "→ ..." / "👉 ..." — ПЕРЕД всеми emoji-ветками
        if stripped.startswith("→ Нам:"):
            text = stripped[len("→ Нам:") :].strip()
            close_bullets()
            out.append(f"<blockquote><strong>→ Нам:</strong> {md_inline(text)}</blockquote>")
            continue
        if stripped.startswith("→ "):
            text = stripped[2:].strip()
            close_bullets()
            out.append(f"<blockquote><strong>→</strong> {md_inline(text)}</blockquote>")
            continue
        if stripped.startswith("👉"):
            text = stripped.lstrip("👉").strip()
            close_bullets()
            if text.lower().startswith("как применить:"):
                text = text.split(":", 1)[1].strip()
                out.append(
                    f'<blockquote><strong>👉 Как применить:</strong> {md_inline(text)}</blockquote>'
                )
            else:
                out.append(f"<blockquote><strong>👉</strong> {md_inline(text)}</blockquote>")
            continue

        # Нумерованный пункт "1. Title"
        m = re.match(r"^(\d+)\.\s+(.+)$", s)
        if m:
            close_bullets()
            out.append(
                f'<h3 class="numbered" data-n="{m.group(1)}">{md_inline(m.group(2))}</h3>'
            )
            continue

        # Секционный заголовок (начинается с эмодзи)
        if EMOJI_HEAD.match(s):
            close_bullets()
            out.append(f"<h2>{md_inline(s)}</h2>")
            continue

        # Буллет
        if stripped.startswith("• ") or stripped.startswith("- "):
            if not in_bullets:
                out.append('<ul class="bullets">')
                in_bullets = True
            out.append(f"<li>{md_inline(stripped[2:].strip())}</li>")
            continue

        close_bullets()

        # Helper-labels: "Что случилось:", "Живой пример:", "Выхлоп:", "Источник:"
        m = re.match(r"^(Что случилось|Живой пример|Источник|Суть|Выхлоп)\s*:\s*(.+)$", s)
        if m:
            out.append(
                f'<p><span class="hint">{html.escape(m.group(1))}</span> {md_inline(m.group(2))}</p>'
            )
            continue

        out.append(f"<p>{md_inline(s)}</p>")

    close_bullets()
    return "\n".join(out)


def build_page(date_str: str, md: str) -> str:
    body = md_to_html(md)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Дайджест {date_str} · ИБ</title>
  <meta name="robots" content="noindex, nofollow">
  <link rel="stylesheet" href="../assets/style.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><circle cx=%2216%22 cy=%2216%22 r=%226%22 fill=%22%23d4a574%22/></svg>">
</head>
<body>
  <div class="topbar">
    <div class="brand"><span class="dot"></span>ИБ · Лента</div>
    <nav>
      <a href="../">Главная</a>
      <a href="./" class="active">Дайджест</a>
      <a href="../dashboard-news/">Дашборд</a>
    </nav>
  </div>
  <div class="container">
    <header class="page-header">
      <div class="kicker">Утренний дайджест · {date_str}</div>
      <h1><em>AI-</em>сводка дня</h1>
      <div class="meta">
        <a href="./">Все выпуски</a>
        <span class="sep">·</span>
        <span>OpenClaw · Claude Code · GitHub · Reddit · HN</span>
      </div>
    </header>
    {body}
    <footer class="page-footer">
      <span>Сгенерировано автоматически</span>
      <a href="https://github.com/instrumentburg-sudo/ib-digest">source</a>
    </footer>
  </div>
</body>
</html>
"""


def first_line_preview(md: str) -> str:
    for line in md.splitlines():
        s = line.strip()
        if not s or s.startswith("🔍"):
            continue
        if len(s) > 5:
            return s[:120]
    return ""


def update_index(date_str: str, preview: str):
    idx = DIGEST_DIR / "index.html"
    content = idx.read_text()
    item = (
        f'      <li><a href="{date_str}.html">Дайджест {date_str}</a>'
        f'<span class="preview">{html.escape(preview)}</span>'
        f'<span class="date">{date_str}</span></li>\n'
    )
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
    page = build_page(date_str, md)
    out = DIGEST_DIR / f"{date_str}.html"
    out.write_text(page)
    update_index(date_str, first_line_preview(md))
    print(f"Wrote {out}")
    print(f"URL: https://instrumentburg-sudo.github.io/ib-digest/digest/{date_str}.html")


if __name__ == "__main__":
    main()
