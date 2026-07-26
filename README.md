# ib-digest

GitHub Pages для **ИнструментБург**:
- 📡 Утренний AI-дайджест (релизы OpenClaw/Claude Code, GitHub trending, Reddit/HN, X через Grok `x_search`)
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

Обновляется через Hermes cron (`~/.hermes/cron/jobs.json`):

- `morning-tech-digest-ekb-1100` (`2c8c45566419`) — 11:00 EKB (`0 8 * * *` на сервере UTC+2): собирает дайджест → `python3 scripts/render-digest.py <md> <date>` → git commit+push → `hermes send --to telegram:292811651`
- `dashboard-daily-pipeline-ekb-1800` (`8819134121ff`) — 18:00 EKB: `apps/dashboard/run-daily-pipeline.sh` → Dashboard News на GitHub Pages

### X / Twitter

Только tool `x_search` (xAI Grok + подписка SuperGrok / X Premium+ через `hermes auth add xai-oauth`).  
Не использовать clawd `x-research`, xurl и web-search по x.com.

## Локальный запуск

```bash
# Дайджест из MD-файла
python3 scripts/render-digest.py /path/to/digest.md 2026-04-16

# Dashboard News из apps/dashboard/
python3 scripts/render-dashboard-news.py /home/iamsohappy/projects/instrumentburg/apps/dashboard 2026-04-16
```
