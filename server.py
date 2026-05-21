from flask import Flask, request, jsonify, render_template_string, send_from_directory
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os, json, uuid

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


def normalize_on_time(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes")
    return bool(val)


def save_record(rec):
    fname = f"scan_{datetime.now(ZoneInfo('Asia/Yerevan')).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.json"
    path = os.path.join(SAVE_FOLDER, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"Saved: {path}")
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
    count = sum(1 for f in os.listdir(SAVE_FOLDER) if f.endswith(".json"))
    return jsonify({"count": count})


@app.route("/upload", methods=["GET", "POST"])
def upload():
    erevan_now = datetime.now(ZoneInfo("Asia/Yerevan"))

    if request.method == "POST":
        if not request.is_json:
            return jsonify({"status": "error", "msg": "expected JSON"}), 400

        payload = request.get_json()
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

        filename = save_record(record)
        msg = "Ժամանակին ✅" if on_time else "Ուշացում ❌"
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
            return f"<p>Կոդի համար գրառումներ չկան՝ {code}</p>", 404

        on_time_val = normalize_on_time(record.get("on_time"))
        html_template = """
        <h2>QR ստուգման արդյունք</h2>
        <p>Օգտատեր: {{ record['user_type'] }}</p>
        <p>Սարք: {{ record['device'] }}</p>
        <p>Ուղարկման ժամը: {{ record['time_sent'] }}</p>
        <p>Ստացման ժամը (Երևան): {{ record['received_at'][:19] }}</p>
        <p>Կարգավիճակ: {% if on_time %}Ժամանակին ✅{% else %}Ուշացում ❌{% endif %}</p>
        <p><a href="/files/{{ filename }}" target="_blank">📄 Ներբեռնել JSON</a></p>
        """
        return render_template_string(html_template, record=record, filename=filename, on_time=on_time_val)


@app.route("/files/<filename>")
def get_file(filename):
    return send_from_directory(SAVE_FOLDER, filename, as_attachment=True)

@app.route("/files", methods=["GET"])
def list_files():
    return jsonify({"files": os.listdir(SAVE_FOLDER)})


ALL_SCANS_HTML = """<!DOCTYPE html>
<html lang="hy">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Հաճախումների Մատյան</title>
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
  tbody tr { transition: background 0.15s; animation: fadeIn 0.3s ease both; }
  tbody tr:hover td { background: var(--gray-100); }
  .col-name { font-family: 'EB Garamond', serif; font-size: 16px; color: var(--black); }
  .col-time { color: var(--gray-600); font-size: 12px; letter-spacing: 0.04em; }
  .badge { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 500; letter-spacing: 0.12em; text-transform: uppercase; padding: 4px 10px; border-radius: 2px; }
  .badge-pass { background: var(--black); color: var(--white); }
  .badge-fail { background: transparent; color: var(--gray-400); border: 1px solid var(--gray-200); }
  .badge svg { width: 11px; height: 11px; flex-shrink: 0; }
  .row-num { color: var(--gray-200); font-size: 11px; width: 40px; padding-left: 48px; padding-right: 0; }
  footer { border-top: 1px solid var(--gray-200); padding: 20px 48px; font-size: 11px; color: var(--gray-400); letter-spacing: 0.08em; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
  {% for i in range(records|length) %}
  tbody tr:nth-child({{ i+1 }}) { animation-delay: {{ i * 0.03 }}s; }
  {% endfor %}
</style>
</head>
<body>
<header>
  <div class="logo">Հաճախումների Մատյան</div>
  <div class="date-label" id="today-date"></div>
</header>
<div class="meta-bar">
  <div class="meta-item">Ընդամենը՝ <span>{{ total }}</span></div>
  <div class="meta-item">Ժամանակին՝ <span>{{ pass_count }}</span></div>
  <div class="meta-item">Ուշացում՝ <span>{{ fail_count }}</span></div>
</div>
<table>
  <thead><tr>
    <th style="width:60px;">#</th>
    <th>Անուն</th>
    <th>Ժամանակ</th>
    <th>Կարգավիճակ</th>
  </tr></thead>
  <tbody>
    {% for r in records %}
    <tr>
      <td class="row-num">{{ loop.index }}</td>
      <td class="col-name">{{ r.user_type }}</td>
      <td class="col-time">{{ r.received_at_formatted }}</td>
      <td>
        {% if r.on_time_bool %}
          <span class="badge badge-pass">
            <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M2 6L5 9L10 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Ժամանակին
          </span>
        {% else %}
          <span class="badge badge-fail">
            <svg viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M3 3L9 9M9 3L3 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            Ուշացում
          </span>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
<footer id="footer-ts"></footer>
<script>
  const now = new Date();
  const months = ['հունվարի','Փետրվարի','Մարտի','Ապրիլի','Մայիսի','Հունիսի','Հուլիսի','Օգոստոսի','Սեպտեմբերի','Հոկտեմբերի','Նոյեմբերի','Դեկտեմբերի'];
  document.getElementById('today-date').textContent =
    now.getDate() + ' ' + months[now.getMonth()] + ' ' + now.getFullYear();
  document.getElementById('footer-ts').textContent =
    'Վերջին թարմացում ' + now.toLocaleTimeString('ru-RU');

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
    all_records = []
    files = sorted(os.listdir(SAVE_FOLDER), reverse=True)
    for file in files:
        if file.endswith(".json"):
            path = os.path.join(SAVE_FOLDER, file)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                dt = datetime.fromisoformat(data.get("received_at"))
                data["received_at_formatted"] = dt.strftime("%d.%m.%Y  %H:%M:%S")
                data["on_time_bool"] = normalize_on_time(data.get("on_time"))
                all_records.append(data)

    pass_count = sum(1 for r in all_records if r["on_time_bool"])
    fail_count = len(all_records) - pass_count

    return render_template_string(
        ALL_SCANS_HTML,
        records=all_records,
        count=len(all_records),
        total=len(all_records),
        pass_count=pass_count,
        fail_count=fail_count,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
