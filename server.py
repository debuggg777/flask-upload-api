from flask import Flask, request, jsonify, render_template_string, send_from_directory
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os, json, uuid

import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

SAVE_FOLDER = "received_json"
os.makedirs(SAVE_FOLDER, exist_ok=True)

VALID = {
    "ABC1": {"type": "Վահե Այվազյան"},
    "ABC2": {"type": "Նարեկ Թովմասյան"},
    "ABC3": {"type": "Արտյոմ Եղիազարյան"},
    "ABC4": {"type": "Էվն Իգազարյան"},
    "ABC5": {"type": "Էրիկ Եղոյան"},
    "ABC6": {"type": "Մարիաննա Վանիյան"},
    "ABC7": {"type": "Միլենա Աղաջանյան"},
    "ABC8": {"type": "Էդգար Առաքելյան"},
    "ABC9": {"type": "Անի Աղաջանյան"},
    "ABC10": {"type": "Միլենա Գրիգորյան"},
    "ABC11": {"type": "Արտյոմ Թավադյան"},
    "ABC12": {"type": "Սարգիս Խաչատրյան"},
    "ABC13": {"type": "Էլլադա Հայրապետյան"},
    "ABC14": {"type": "Էլզա Հովհանիսյան"},
    "ABC15": {"type": "Արմինե Սարգսյան"},
    "ABC16": {"type": "Արման Գրիգորյան"},
    "ABC17": {"type": "Էլվնիա Բաբայան"},
    "ABC18": {"type": "Անահիտ Ղազարյան"},
    "ABC19": {"type": "Եվա Մանուկյան"},
    "ABC20": {"type": "Մարի Մարտիրոսյան"},
    "ABC21": {"type": "Քնարիկ Մարտիրոսյան"},
    "ABC22": {"type": "Կարինա Ստեպանյան"},
    "ABC23": {"type": "Սոնա Վարդանյան"},
    "ABC24": {"type": "Սյուզի Չոբանյան"},
    "ABC25": {"type": "Անի Մամիկոնյան"},
    "ABC26": {"type": "Մանե Գասպարյան"},
    "ABC27": {"type": "Էմիլ Խաչատրյան"}
}

# --- Google Sheets setup ---
def get_sheet():
    raw = os.environ.get("GOOGLE_CREDENTIALS", "")
    creds_dict = json.loads(raw)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet_id = os.environ.get("SHEET_ID", "")
    sh = client.open_by_key(sheet_id)
    # Берём первый лист, создаём заголовки если пустой
    ws = sh.sheet1
    if ws.row_count == 0 or ws.cell(1, 1).value != "Имя":
        ws.insert_row(["Имя", "Код", "Устройство", "Время отправки", "Время получения (Ереван)", "Статус"], index=1)
    return ws


def append_to_sheet(record):
    try:
        ws = get_sheet()
        status = "Вовремя" if record.get("on_time") else "Опоздание"
        ws.append_row([
            record.get("user_type", "—"),
            record.get("code", "—"),
            record.get("device", "—"),
            record.get("time_sent", "—"),
            record.get("received_at", "—")[:19],
            status,
        ])
    except Exception as e:
        print(f"[Sheets ERROR] {e}")


def read_from_sheet():
    try:
        ws = get_sheet()
        rows = ws.get_all_records()
        return rows
    except Exception as e:
        print(f"[Sheets READ ERROR] {e}")
        return []


# --- Локальный бэкап (на случай если Sheets недоступен) ---
def save_record_local(rec):
    fname = f"scan_{datetime.now(ZoneInfo('Asia/Yerevan')).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.json"
    path = os.path.join(SAVE_FOLDER, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return fname


def get_last_record_by_code(code):
    files = sorted(os.listdir(SAVE_FOLDER), reverse=True)
    for file in files:
        if file.endswith(".json"):
            path = os.path.join(SAVE_FOLDER, file)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("code") == code:
                    return data, file
    return None, None


@app.route("/scan_count")
def scan_count():
    try:
        ws = get_sheet()
        # минус строка заголовка
        count = max(0, ws.row_count - 1)
        # точнее — считаем непустые строки
        rows = ws.get_all_records()
        return jsonify({"count": len(rows)})
    except Exception:
        count = sum(1 for f in os.listdir(SAVE_FOLDER) if f.endswith(".json"))
        return jsonify({"count": count})


@app.route("/upload", methods=["GET", "POST"])
def upload():
    erevan_now = datetime.now(ZoneInfo("Asia/Yerevan"))

    if request.method == "POST":
        if not request.is_json:
            return jsonify({"status": "error", "msg": "expected JSON"}), 400

        payload = request.get_json()
        print("Received JSON:", payload)

        raw_code = payload.get("code", "{}")
        try:
            code_data = json.loads(raw_code) if isinstance(raw_code, str) else raw_code
        except json.JSONDecodeError:
            code_data = {}

        code = code_data.get("id") or ""
        user_type = code_data.get("type") or "unknown"
        device = payload.get("device", "unknown")
        time_sent = payload.get("time") or erevan_now.isoformat()

        if code in VALID:
            user_type = VALID[code]["type"]

        on_time = erevan_now.time() <= time(8, 20)

        record = {
            "code": code,
            "user_type": user_type,
            "device": device,
            "time_sent": time_sent,
            "received_at": erevan_now.isoformat(),
            "on_time": on_time
        }

        filename = save_record_local(record)
        append_to_sheet(record)  # сохраняем в Google Sheets

        msg = "Пройдено вовремя ✅" if on_time else "Опоздание ❌"
        allowed = on_time if code in VALID else False

        return jsonify({
            "status": "ok" if code in VALID else "error",
            "allowed": allowed,
            "msg": msg,
            "record": record,
            "file": f"/files/{filename}"
        }), 200

    else:
        code = (request.args.get("id") or "").strip()
        record, filename = get_last_record_by_code(code)
        if not record:
            return f"<p>Нет записей для кода {code}</p>", 404

        html_template = """
        <h2>Результат проверки QR</h2>
        <p>Пользователь: {{ record['user_type'] }}</p>
        <p>Устройство: {{ record['device'] }}</p>
        <p>Время отправки: {{ record['time_sent'] }}</p>
        <p>Время получения (Ереван): {{ record['received_at'][:19] }}</p>
        <p>Статус: {% if record['on_time'] %}Пройдено вовремя ✅{% else %}Опоздание ❌{% endif %}</p>
        <p><a href="/files/{{ filename }}" target="_blank">📄 Скачать JSON</a></p>
        """
        return render_template_string(html_template, record=record, filename=filename)


@app.route("/files/<filename>")
def get_file(filename):
    return send_from_directory(SAVE_FOLDER, filename, as_attachment=True)

@app.route("/files", methods=["GET"])
def list_files():
    return jsonify({"files": os.listdir(SAVE_FOLDER)})


ALL_SCANS_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Журнал посещаемости</title>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;500&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --black: #0a0a0a;
    --white: #f8f7f4;
    --gray-100: #f0ede8;
    --gray-200: #ddd9d2;
    --gray-400: #9c9690;
    --gray-600: #5a5652;
  }
  body { background: var(--white); color: var(--black); font-family: 'DM Mono', monospace; min-height: 100vh; }
  header { border-bottom: 2px solid var(--black); padding: 28px 48px; display: flex; align-items: baseline; justify-content: space-between; }
  .logo { font-family: 'EB Garamond', serif; font-size: 22px; font-weight: 500; letter-spacing: 0.02em; }
  .date-label { font-size: 11px; color: var(--gray-400); letter-spacing: 0.12em; text-transform: uppercase; }
  .meta-bar { padding: 14px 48px; border-bottom: 1px solid var(--gray-200); display: flex; gap: 40px; }
  .meta-item { font-size: 11px; color: var(--gray-400); letter-spacing: 0.1em; text-transform: uppercase; }
  .meta-item span { color: var(--black); font-weight: 500; }
  table { width: 100%; border-collapse: collapse; }
  thead tr { border-bottom: 1px solid var(--black); }
  th { font-size: 10px; font-weight: 500; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gray-400); padding: 14px 48px; text-align: left; }
  td { padding: 16px 48px; font-size: 13px; border-bottom: 1px solid var(--gray-100); vertical-align: middle; }
  tbody tr:hover td { background: var(--gray-100); }
  .col-name { font-family: 'EB Garamond', serif; font-size: 16px; }
  .col-time { color: var(--gray-600); font-size: 12px; letter-spacing: 0.04em; }
  .badge { display: inline-block; font-size: 10px; font-weight: 500; letter-spacing: 0.12em; text-transform: uppercase; padding: 4px 10px; border-radius: 2px; }
  .badge-pass { background: var(--black); color: var(--white); }
  .badge-fail { background: transparent; color: var(--gray-400); border: 1px solid var(--gray-200); }
  .row-num { color: var(--gray-200); font-size: 11px; width: 40px; padding-left: 48px; padding-right: 0; }
  footer { border-top: 1px solid var(--gray-200); padding: 20px 48px; font-size: 11px; color: var(--gray-400); letter-spacing: 0.08em; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
  tbody tr { animation: fadeIn 0.3s ease both; }
</style>
</head>
<body>
<header>
  <div class="logo">Журнал посещаемости</div>
  <div class="date-label" id="today-date"></div>
</header>
<div class="meta-bar">
  <div class="meta-item">Всего: <span>{{ records|length }}</span></div>
  <div class="meta-item">Вовремя: <span>{{ pass_count }}</span></div>
  <div class="meta-item">Опоздания: <span>{{ fail_count }}</span></div>
</div>
<table>
  <thead><tr>
    <th style="width:60px;">#</th>
    <th>Имя</th>
    <th>Время</th>
    <th>Статус</th>
  </tr></thead>
  <tbody>
    {% for r in records %}
    <tr>
      <td class="row-num">{{ loop.index }}</td>
      <td class="col-name">{{ r.get('Имя', r.get('user_type', '—')) }}</td>
      <td class="col-time">{{ r.get('Время получения (Ереван)', r.get('received_at_formatted', '—')) }}</td>
      <td>
        {% set s = r.get('Статус', '') %}
        {% set ot = r.get('on_time', s == 'Вовремя') %}
        {% if ot %}
          <span class="badge badge-pass">Вовремя</span>
        {% else %}
          <span class="badge badge-fail">Опоздание</span>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<footer id="footer-ts"></footer>
<script>
  const now = new Date();
  document.getElementById('today-date').textContent =
    now.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' });
  document.getElementById('footer-ts').textContent =
    'Последнее обновление: ' + now.toLocaleTimeString('ru-RU');

  let lastCount = {{ count }};
  setInterval(() => {
    fetch('/scan_count')
      .then(r => r.json())
      .then(d => { if (d.count !== lastCount) location.reload(); })
      .catch(() => {});
  }, 3000);
</script>
</body>
</html>
"""

@app.route("/all_scans_view", methods=["GET"])
def all_scans_view():
    records = read_from_sheet()
    pass_count = sum(1 for r in records if r.get("Статус") == "Вовремя")
    fail_count = sum(1 for r in records if r.get("Статус") == "Опоздание")
    return render_template_string(ALL_SCANS_HTML, records=records,
                                  count=len(records),
                                  pass_count=pass_count,
                                  fail_count=fail_count)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
