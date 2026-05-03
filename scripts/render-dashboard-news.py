#!/usr/bin/env python3
"""Render Dashboard News: insights из apps/dashboard/insights.js → HTML страница."""
import re
import sys
import html
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_DIR = ROOT / "dashboard-news"
EKB = timezone(timedelta(hours=5))
DASHBOARD_URL = "https://dashboard-three-blond-70.vercel.app"

EMOJI_PREFIX = re.compile(
    r"^([\U0001F300-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2300-\u23FF\u2B00-\u2BFF\uFE0F]+\s*)(.+)$"
)


def parse_js_vars(text: str) -> dict:
    """Парсит `var X='...';` и `var X=[...];` и `var X=123;` из JS-файла."""
    out = {}
    for m in re.finditer(r"var\s+([A-Z_]+)\s*=\s*\[([^\]]*)\]\s*;", text):
        name = m.group(1)
        raw = m.group(2).strip()
        if not raw:
            out[name] = []
            continue
        items = []
        try:
            parsed = json.loads(f"[{raw}]")
            if isinstance(parsed, list):
                out[name] = [str(x) for x in parsed]
                continue
        except json.JSONDecodeError:
            pass
        for part in re.finditer(r"'((?:[^'\\]|\\.)*)'", raw):
            items.append(part.group(1).replace("\\'", "'"))
        out[name] = items
    for m in re.finditer(r'var\s+([A-Z_]+)\s*=\s*("(?:[^"\\]|\\.)*")\s*;', text):
        try:
            out[m.group(1)] = json.loads(m.group(2))
        except json.JSONDecodeError:
            pass
    for m in re.finditer(r"var\s+([A-Z_]+)\s*=\s*'((?:[^'\\]|\\.)*)'\s*;", text):
        out[m.group(1)] = m.group(2).replace("\\'", "'")
    for m in re.finditer(r"var\s+([A-Za-z_][\w,=\.\- ]*?)\s*;", text):
        decl = m.group(1)
        if "[" in decl or "'" in decl or '"' in decl:
            continue
        for pair in decl.split(","):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            k, v = k.strip(), v.strip()
            try:
                out[k] = float(v) if "." in v else int(v)
            except ValueError:
                pass
    return out


def fmt_int(v) -> str:
    try:
        return f"{int(v):,}".replace(",", " ")
    except (ValueError, TypeError):
        return "—"


def classify_insight(text: str) -> str:
    low = text.lower()
    if text.lstrip().startswith(("⚠", "🔥")) or "ниже норм" in low or "высок" in low or "проблем" in low:
        return "warn"
    if text.lstrip().startswith("✅") or "отличн" in low or "вырос" in low:
        return "good"
    if "срочно" in low or "критич" in low:
        return "bad"
    return ""


def split_emoji(text: str) -> tuple[str, str]:
    m = EMOJI_PREFIX.match(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", text


def metricize(body: str) -> str:
    """Подсветить цифры/проценты/стрелки как .metric."""
    return re.sub(
        r"(↓|↑|\-?\d+(?:[,\.]\d+)?\s*%|\-?\d[\d\s,]*\s*₽|\-?\d+(?:[,\.]\d+)?\s*(?:тыс|млн|раз))",
        lambda m: f'<span class="metric">{m.group(1).strip()}</span>',
        body,
    )


def render_insight(text: str, kind: str) -> str:
    emoji, body = split_emoji(text)
    css = classify_insight(text)
    body_html = html.escape(body)
    body_html = metricize(body_html)
    emoji_html = f"{html.escape(emoji)} " if emoji else ""
    label = {"action": "→ Что делать", "marketing": "Маркетинг"}.get(kind, "")
    prefix = f'<strong>{html.escape(label)}:</strong> ' if label else ""
    return f'<div class="card {css}"><p>{emoji_html}{prefix}{body_html}</p></div>'


def render_stale_banner(v: dict) -> str:
    status = str(v.get("LIVE_SKLAD_STATUS") or "ok")
    if status == "ok":
        return ""
    message = str(v.get("LIVE_SKLAD_MESSAGE") or "LiveSklad stale — данные заказов могут быть устаревшими")
    return (
        '<div class="card warn"><p>⚠️ '
        f'{metricize(html.escape(message))}'
        '</p></div>'
    )


def render_summary(v: dict) -> str:
    cells = [
        ("Сегодня", fmt_int(v.get("TODAY_REV")), "₽", f"{v.get('TODAY_ORDERS', 0)} заказов"),
        ("Вчера", fmt_int(v.get("YEST_REV")), "₽", f"{v.get('YEST_ORDERS', 0)} заказов"),
        (
            "Средние будни",
            fmt_int(v.get("AVG_WD_REV")),
            "₽",
            f"{v.get('AVG_WD_ORDERS', 0)} заказов",
        ),
        (
            "Ремонт · Аренда",
            f"{v.get('TODAY_REPAIR', 0)} · {v.get('TODAY_RENTAL', 0)}",
            "",
            f"Закрыто: {v.get('TODAY_CLOSED', 0)}",
        ),
    ]
    parts = ['<div class="kpi-grid">']
    for label, value, unit, sub in cells:
        value_cls = ""
        try:
            num = int(str(value).replace(" ", ""))
            if num < 0:
                value_cls = " neg"
        except ValueError:
            pass
        parts.append(
            f'<div class="kpi">'
            f'<span class="kpi-label">{html.escape(label)}</span>'
            f'<span class="kpi-value{value_cls}">{html.escape(str(value))}'
        )
        if unit:
            parts.append(f'<span class="unit">{html.escape(unit)}</span>')
        parts.append("</span>")
        if sub:
            parts.append(f'<span class="kpi-sub">{html.escape(sub)}</span>')
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


def render_list(items: list[str], kind: str) -> str:
    return "\n".join(render_insight(x, kind) for x in items) if items else ""


def build_page(date_str: str, label: str, summary: str, insights: str, actions: str, marketing: str) -> str:
    sections = []
    if insights:
        sections.append(f'<h2>Инсайты</h2>\n{insights}')
    if actions:
        sections.append(f'<h2>К действию</h2>\n{actions}')
    if marketing:
        sections.append(f'<h2>Маркетинг</h2>\n{marketing}')
    if not sections:
        sections.append('<div class="card"><p>Сегодня без новых инсайтов — дашборд стабилен.</p></div>')
    body = "\n".join(sections)
    kicker = f"Сводка · {label}" if label else f"Сводка · {date_str}"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard News {date_str} · ИБ</title>
  <meta name="robots" content="noindex, nofollow">
  <link rel="stylesheet" href="../assets/style.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 32 32%22><circle cx=%2216%22 cy=%2216%22 r=%226%22 fill=%22%23d4a574%22/></svg>">
</head>
<body>
  <div class="topbar">
    <div class="brand"><span class="dot"></span>ИБ · Лента</div>
    <nav>
      <a href="../">Главная</a>
      <a href="../digest/">Дайджест</a>
      <a href="./" class="active">Дашборд</a>
    </nav>
  </div>
  <div class="container">
    <header class="page-header">
      <div class="kicker">{html.escape(kicker)}</div>
      <h1>Dashboard <em>News</em></h1>
      <div class="meta">
        <a href="./">Все выпуски</a>
        <span class="sep">·</span>
        <a href="{DASHBOARD_URL}" target="_blank" rel="noopener">Открыть дашборд</a>
      </div>
    </header>
    {summary}
    {body}
    <footer class="page-footer">
      <span>Источник: apps/dashboard/insights.js</span>
      <a href="https://github.com/instrumentburg-sudo/ib-digest">source</a>
    </footer>
  </div>
</body>
</html>
"""


def first_preview(v: dict) -> str:
    items = v.get("ACTIONS", []) + v.get("INSIGHTS", []) + v.get("MARKETING", [])
    for t in items:
        _, body = split_emoji(t)
        if body:
            return body[:120]
    return "без новых инсайтов"


def update_index(date_str: str, preview: str):
    idx = NEWS_DIR / "index.html"
    content = idx.read_text()
    item = (
        f'      <li><a href="{date_str}.html">Dashboard News {date_str}</a>'
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
        print("Usage: render-dashboard-news.py <dashboard-dir> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)
    dash_dir = Path(sys.argv[1])
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now(EKB).strftime("%Y-%m-%d")

    text = ""
    for p in [dash_dir / "insights.js", dash_dir / "data.js"]:
        if p.exists():
            text += p.read_text() + "\n"
    v = parse_js_vars(text)

    summary = render_stale_banner(v) + render_summary(v)
    insights = render_list(v.get("INSIGHTS", []), "insight")
    actions = render_list(v.get("ACTIONS", []), "action")
    marketing = render_list(v.get("MARKETING", []), "marketing")
    label = v.get("TODAY_LABEL", date_str)

    page = build_page(date_str, label, summary, insights, actions, marketing)
    out = NEWS_DIR / f"{date_str}.html"
    out.write_text(page)
    update_index(date_str, first_preview(v))
    print(f"Wrote {out}")
    print(f"URL: https://instrumentburg-sudo.github.io/ib-digest/dashboard-news/{date_str}.html")


if __name__ == "__main__":
    main()
