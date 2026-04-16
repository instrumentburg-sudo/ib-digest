# ib-digest

GitHub Pages для **ИнструментБург**:
- 📡 Утренний AI-дайджест (релизы OpenClaw/Claude Code, GitHub trending, Reddit/HN)
- 📊 Dashboard News (ежедневные инсайты из `apps/dashboard/insights.js`)

Публикация: https://instrumentburg-sudo.github.io/ib-digest/

## Структура

```
ib-digest/
├── index.html              лендинг со ссылками
├── digest/
│   ├── index.html          список выпусков дайджеста
│   └── YYYY-MM-DD.html
├── dashboard-news/
│   ├── index.html
│   └── YYYY-MM-DD.html
├── scripts/
│   ├── render-digest.py           MD → HTML
│   └── render-dashboard-news.py   insights.js → HTML
└── assets/style.css
```

## Как работает cron

Обновляется через OpenClaw cron (`~/.openclaw/cron/jobs.json`):

- `morning-tech-digest` — 11:00 EKB: собирает дайджест → `python3 scripts/render-digest.py <md> <date>` → git commit+push → Telegram со ссылкой
- `dashboard-daily-update` — 18:00 EKB: `apps/dashboard/update-data.sh` → `python3 scripts/render-dashboard-news.py apps/dashboard <date>` → git commit+push → Telegram со ссылкой

## Локальный запуск

```bash
# Дайджест из MD-файла
python3 scripts/render-digest.py /path/to/digest.md 2026-04-16

# Dashboard News из apps/dashboard/
python3 scripts/render-dashboard-news.py /home/iamsohappy/projects/instrumentburg/apps/dashboard 2026-04-16
```
