from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

from .app import run_once
from .config import AppConfig
from .credentials import save_credentials_to_env
from .reporting import load_latest_generated_time, load_latest_summary_rows


def create_web_app(config: AppConfig) -> Flask:
    app = Flask(__name__)
    lock = threading.Lock()
    state = {"running": False, "last_error": "", "last_run": ""}
    env_path = Path(".env")

    @app.get("/")
    def index():
        rows = load_latest_summary_rows(config.output_dir)
        generated_at = load_latest_generated_time(config.output_dir) or state["last_run"]
        timezone = ZoneInfo(config.timezone)
        now_text = datetime.now(tz=timezone).isoformat(timespec="seconds")
        return render_template_string(
            _HTML_TEMPLATE,
            rows=rows,
            generated_at=generated_at,
            running=state["running"],
            last_error=state["last_error"],
            now_text=now_text,
            timezone=config.timezone,
            has_credentials=bool(config.username and config.password),
            username=config.username,
        )

    @app.post("/save-credentials")
    def save_credentials():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            state["last_error"] = "Моля въведете потребител и парола."
            return redirect(url_for("index"))

        save_credentials_to_env(env_path, username, password)
        config.username = username
        config.password = password
        state["last_error"] = ""
        return redirect(url_for("index"))

    @app.post("/run-now")
    def run_now():
        if state["running"]:
            return redirect(url_for("index"))
        with lock:
            state["running"] = True
            state["last_error"] = ""
        try:
            result = run_once(config)
            state["last_run"] = result["run_time"].isoformat(timespec="seconds")
        except Exception as exc:  # pragma: no cover - runtime route
            state["last_error"] = str(exc)
        finally:
            state["running"] = False
        return redirect(url_for("index"))

    @app.get("/api/status")
    def status():
        rows = load_latest_summary_rows(config.output_dir)
        return jsonify(
            {
                "running": state["running"],
                "last_error": state["last_error"],
                "last_run": load_latest_generated_time(config.output_dir) or state["last_run"],
                "rows": rows,
            }
        )

    return app


_HTML_TEMPLATE = """
<!doctype html>
<html lang="bg">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SOFCOM Local Dashboard</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      font-family: Arial, sans-serif;
      margin: 24px;
      max-width: 1000px;
    }
    h1 { margin-bottom: 0.25rem; }
    .meta { color: #666; margin-bottom: 1rem; }
    .row { display: flex; gap: 12px; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
    button {
      border: none;
      border-radius: 8px;
      padding: 10px 16px;
      background: #2d6cdf;
      color: white;
      cursor: pointer;
      font-size: 14px;
    }
    button:disabled { opacity: 0.6; cursor: default; }
    .error {
      padding: 10px;
      border-radius: 8px;
      background: #fce8e6;
      color: #8d1b14;
      margin-bottom: 1rem;
    }
    .card {
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 1rem;
    }
    label { display: block; margin-bottom: 4px; font-weight: 600; }
    input[type="text"], input[type="password"] {
      width: 100%;
      max-width: 420px;
      padding: 8px;
      border-radius: 6px;
      border: 1px solid #bbb;
      margin-bottom: 10px;
      font-size: 14px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }
    th, td {
      border: 1px solid #ddd;
      padding: 8px;
      text-align: right;
    }
    th:nth-child(1), th:nth-child(2), td:nth-child(1), td:nth-child(2) { text-align: left; }
    .empty { margin-top: 1rem; color: #666; }
    code { background: #f5f5f5; padding: 2px 4px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>SOFCOM Local Dashboard</h1>
  <div class="meta">Локално време ({{ timezone }}): {{ now_text }}</div>
  <div class="card">
    <h3>Вход в системата</h3>
    <form method="post" action="{{ url_for('save_credentials') }}">
      <label for="username">Потребител</label>
      <input id="username" name="username" type="text" value="{{ username or '' }}" autocomplete="username" />
      <label for="password">Парола</label>
      <input id="password" name="password" type="password" autocomplete="current-password" />
      <button type="submit">Запази вход данни</button>
    </form>
    <div style="margin-top: 8px;">
      Статус: {% if has_credentials %}<strong>готово</strong>{% else %}<strong>липсват данни</strong>{% endif %}
    </div>
  </div>
  <div class="row">
    <form method="post" action="{{ url_for('run_now') }}">
      <button type="submit" {% if running or not has_credentials %}disabled{% endif %}>
        {% if running %}Изпълнява се...{% else %}Run now{% endif %}
      </button>
    </form>
    <div>Последно генериран отчет: <strong>{{ generated_at or "няма" }}</strong></div>
  </div>
  {% if last_error %}
    <div class="error"><strong>Грешка:</strong> {{ last_error }}</div>
  {% endif %}
  {% if rows %}
    <table>
      <thead>
        <tr>
          <th>Действие</th>
          <th>Подразделение</th>
          <th>Брой</th>
          <th>Сума</th>
          <th>Тегло в гр</th>
        </tr>
      </thead>
      <tbody>
      {% for row in rows %}
        <tr>
          <td>{{ row["Действие"] }}</td>
          <td>{{ row["Подразделение"] }}</td>
          <td>{{ row["Брой"] }}</td>
          <td>{{ row["Сума"] }}</td>
          <td>{{ row["Тегло в гр"] }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="empty">
      Все още няма генериран отчет. Натисни <strong>Run now</strong> или стартирай
      <code>python main.py --run-now</code>.
    </p>
  {% endif %}
</body>
</html>
"""
