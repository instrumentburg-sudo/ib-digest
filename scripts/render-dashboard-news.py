#!/usr/bin/env python3
"""Render Dashboard News: insights из apps/dashboard/insights.js → HTML страница."""
import re
import sys
import html
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEWS_DIR = ROOT / "dashboard-news"
EKB = timezone(timedelta(hours=5))
DASHBOARD_URL = "https://dashboard-three-blond-70.vercel.app"


def parse_js_vars(text: str) -> dict:
    """Парсит `var X='...';` и `var X=[...];` и `var X=123;` из JS-файла.
    Возвращает dict с примитивами/строками/списками строк."""
    out = {}
    # Строковые массивы: var NAME=['a','b',...];
    for m in re.finditer(r"var\s+([A-Z_]+)\s*=\s*\[([^\]]*)\]\s*;", text):
        name = m.group(1)
        raw = m.group(2).strip()
        if not raw:
            out[name] = []
            continue
        items = []
        for part in re.finditer(r"'((?:[^'\\]|\\.)*)'", raw):
            items.append(part.group(1).replace("\\'", "'"))
        out[name] = items
    # Строковые скаляры: var NAME='...';
    for m in re.finditer(r"var\s+([A-Z_]+)\s*=\s*'((?:[^'\\]|\\.)*)'\s*;", text):
        out[m.group(1)] = m.group(2).replace("\\'", "'")
    # Числовые скаляры / составные: var A=1,B=2,C=3.4;
    for m in re.finditer(r"var\s+([A-Za-z_][\w,=\.\- ]*?)\s*;", text):
        decl = m.group(1)
        # Пропускаем уже разобранные массивы/строки
        if "[" in decl or "'" in decl or '"' in decl:
            continue
        for pair in decl.split(","):
            if "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()
            try:
                out[k] = float(v) if "." in v else int(v)
            except ValueError:
                pass
    return out


def classify_insight(text: str) -> str:
    """По содержимому выбираем цвет карточки."""
    low = text.lower()
    if text.startswith("⚠️") or "ниже" in low or "высок" in low or "проблем" in low:
        return "warn"
    if "отличн" in low or "выросл" in low or "рост" in low or text.startswith("✅"):
        return "good"
    if text.startswith("🔥") or "срочно" in low:
        return "bad"
    return ""


def split_emoji(text: str) -> tuple[str, str]:
    """Отделить ведущий emoji от остального текста."""
    m = re.match(r"^([\U0001F300-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\u2300-\u23FF]+\s*)(.+)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", text


def render_insight(text: str, kind: str) -> str:
    emoji, body = split_emoji(text)
    css = classify_insight(text)
    body_html = html.escape(body)
    # Цифры с процентами/стрелками подсветим как metric
    body_html = re.sub(
        r"(↓|↑|\-?\d+(?:[,\.]\d+)?%|\-?\d[\d,]*\s*₽)",
        lambda m: f'<span class="metric">{m.group(1)}</span>',
        body_html,
    )
    emoji_html = html.escape(emoji) + " " if emoji else ""
    label = {"action": "→ Что делать", "marketing": "📣 Маркетинг", "insight": ""}.get(kind, "")
    prefix = f'<strong>{label}:</strong> ' if label else ""
    return f'<div class="card {css}"><p style="margin:0">{emoji_html}{prefix}{body_html}</p></div>'


def render_summary(vars_: dict) -> str:
    rows = []
    def row(label, value, suffix=""):
        if value is None:
            return
        rows.append(f'<span class="metric">{label}: {value}{suffix}</span>')

    row("Сегодня заказов", vars_.get("TODAY_ORDERS"))
    row("Сегодня выручка", f"{vars_.get('TODAY_REV'):,}".replace(",", " "), "₽") if vars_.get("TODAY_REV") is not None else None
    row("Вчера заказов", vars_.get("YEST_ORDERS"))
    row("Вчера выручка", f"{vars_.get('YEST_REV'):,}".replace(",", " "), "₽") if vars_.get("YEST_REV") is not None else None
    row("Средн. будни заказов", vars_.get("AVG_WD_ORDERS"))
    row("Средн. будни выручка", f"{vars_.get('AVG_WD_REV'):,}".replace(",", " "), "₽") if vars_.get("AVG_WD_REV") is not None else None
    if vars_.get("TODAY_REPAIR") is not None:
        rows.append(f'<span class="metric">Ремонт: {vars_["TODAY_REPAIR"]}</span>')
    if vars_.get("TODAY_RENTAL") is not None:
        rows.append(f'<span class="metric">Аренда: {vars_["TODAY_RENTAL"]}</span>')
    if vars_.get("TODAY_CLOSED") is not None:
        rows.append(f'<span class="metric">Закрыто: {vars_["TODAY_CLOSED"]}</span>')

    if not rows:
        return ""
    label = vars_.get("TODAY_LABEL", "")
    title = f"Ключевые цифры — {label}" if label else "Ключевые цифры"
    return f'<div class="card"><h3 style="margin-top:0">{html.escape(title)}</h3><p>{"".join(rows)}</p></div>'


def build_page(date_str: str, summary_html: str, insights_html: str, actions_html: str, marketing_html: str) -> str:
    sections = [summary_html]
    if insights_html:
        sections.append(f"<h2>Инсайты</h2>\n{insights_html}")
    if actions_html:
        sections.append(f"<h2>К действию</h2>\n{actions_html}")
    if marketing_html:
        sections.append(f"<h2>Маркетинг</h2>\n{marketing_html}")
    body = "\n".join(s for s in sections if s)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard News {date_str}</title>
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
  <div class="container">
    <header>
      <h1>📊 Dashboard News — {date_str}</h1>
      <div class="meta"><a href="./" class="back">← все выпуски</a> · <a href="{DASHBOARD_URL}" target="_blank">открыть дашборд</a></div>
    </header>
    {body}
    <footer>Источник: <code>apps/dashboard/insights.js</code> · обновляется ежедневно 18:00 EKB</footer>
  </div>
</body>
</html>
"""


def render_list(items: list[str], kind: str) -> str:
    return "\n".join(render_insight(x, kind) for x in items) if items else ""


def first_preview(vars_: dict) -> str:
    items = vars_.get("ACTIONS", []) + vars_.get("INSIGHTS", []) + vars_.get("MARKETING", [])
    for t in items:
        _, body = split_emoji(t)
        if body:
            return body[:90]
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
        print("Usage: render-dashboard-news.py <path-to-dashboard-dir> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)
    dash_dir = Path(sys.argv[1])
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now(EKB).strftime("%Y-%m-%d")

    insights_path = dash_dir / "insights.js"
    data_path = dash_dir / "data.js"
    text = ""
    if insights_path.exists():
        text += insights_path.read_text() + "\n"
    if data_path.exists():
        text += data_path.read_text()
    vars_ = parse_js_vars(text)

    summary = render_summary(vars_)
    insights = render_list(vars_.get("INSIGHTS", []), "insight")
    actions = render_list(vars_.get("ACTIONS", []), "action")
    marketing = render_list(vars_.get("MARKETING", []), "marketing")

    page = build_page(date_str, summary, insights, actions, marketing)
    out = NEWS_DIR / f"{date_str}.html"
    out.write_text(page)
    update_index(date_str, first_preview(vars_))
    print(f"Wrote {out}")
    print(f"URL: https://instrumentburg-sudo.github.io/ib-digest/dashboard-news/{date_str}.html")


if __name__ == "__main__":
    main()
