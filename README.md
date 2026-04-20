# SOFCOM Daily Tracking Scraper

Local Python app that:

- logs in to `https://sofcom.nraposoft.com/Default`
- navigates to `https://sofcom.nraposoft.com/Pages/Tracking/TrackingForm`
- collects action data across pages (and optional action filter options)
- aggregates results into a readable table with these required groups:
  - `Продажби` -> `Жълт метал`, `Злато`, `Сребро`, `Техника`
  - `Презалагане`
  - `Прекратяване`
  - `Нов договор`
- outputs columns:
  - `Брой`
  - `Сума`
  - `Тегло в гр`
- runs daily at 19:00 Bulgarian time (`Europe/Sofia`) when started in daemon mode.

## 1) Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## 2) Configure credentials

Copy env template and fill in your real login details:

```bash
cp .env.example .env
```

Set:

- `SOFCOM_USERNAME`
- `SOFCOM_PASSWORD`

The app handles captcha automatically with OCR (4 digits).

## 3) Run once now

```bash
python main.py --run-now
```

Generated files go in `output/`:

- `latest_summary.md` (readable table)
- `latest_summary.csv`
- `latest_raw.json`

Each run also saves timestamped files.

## 4) Run daily scheduler at 19:00 Sofia time

```bash
python main.py --daemon
```

Default schedule is 19:00 in `Europe/Sofia`.
You can change this with:

- `SOFCOM_SCHEDULE_HOUR`
- `SOFCOM_SCHEDULE_MINUTE`
- `SOFCOM_TIMEZONE`

## 5) Optional selectors for "all actions"

If the Tracking form has a specific action dropdown/filter, set these in `.env`:

- `SOFCOM_ACTION_SELECT_SELECTOR`
- `SOFCOM_ACTION_SEARCH_BUTTON_SELECTOR`

When configured, the scraper iterates all action options and merges results.

## 6) Най-лесно за ползване (без technical стъпки)

Стартирай само:

```bash
python main.py
```

Ще се отвори автоматично страницата:

- http://127.0.0.1:8080

В страницата:

1. попълваш **Потребител** и **Парола**
2. натискаш **Запази вход данни**
3. натискаш **Run now**

Няма нужда да редактираш `.env` ръчно.

### Ако искаш ръчно управление на web mode

```bash
python main.py --web
```

Опции:

```bash
python main.py --web --host 0.0.0.0 --port 8080
python main.py --web --no-browser
```

## 7) Optional run via cron (instead of daemon)

Example cron entry (daily 19:00 Europe/Sofia):

```cron
0 19 * * * cd /workspace && /workspace/.venv/bin/python /workspace/main.py --run-now >> /workspace/output/cron.log 2>&1
```
