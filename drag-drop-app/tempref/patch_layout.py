"""One-off patch: layout tidy - unified buttons, RO links to both stations,
station-aware tab title. Safe to delete after use."""
import io

def load(path):
    with io.open(path, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def save(path, content):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)

def apply(content, old, new, label):
    for o, n in ((old, new), (old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))):
        if content.count(o) == 1:
            print('OK  :', label)
            return content.replace(o, n)
    raise SystemExit('FAIL: %s (LF=%d CRLF=%d)' % (
        label, content.count(old), content.count(old.replace('\n', '\r\n'))))

# ---------- app.py: finishsheet route passes station (tab title) ----------
p = 'app.py'
c = load(p)
c = apply(c,
    "@app.route('/finishsheet')\ndef finishsheet():\n    \"\"\"Render finish sheet UI for race officer scoring.\"\"\"\n    return render_template('finishsheet.html')",
    "@app.route('/finishsheet')\ndef finishsheet():\n    \"\"\"Render finish sheet UI for race officer scoring. The station number\n"
    "    (?station=1|2, default 1) is passed to the template for the tab title;\n"
    "    the JS reads the same URL parameter for the station identity.\"\"\"\n"
    "    station = request.args.get('station', type=int)\n"
    "    if station not in (1, 2):\n"
    "        station = 1\n"
    "    return render_template('finishsheet.html', station=station)",
    'A1: finishsheet route station')
save(p, c)

# ---------- templates/finishsheet.html ----------
p = 'templates/finishsheet.html'
c = load(p)

c = apply(c,
    "    <title>Finish Sheet - Race Scoring</title>",
    "    <title>Finish sheet {{ station }}</title>",
    'F1: station tab title')

c = apply(c,
    "        .btn {\n            padding: 12px 24px;\n            font-weight: bold;\n            border: none;\n            border-radius: 6px;\n            cursor: pointer;\n            font-size: 14px;\n            transition: transform 0.1s;\n        }",
    "        /* Unified button spec - same metrics as the RO control page */\n"
    "        .btn {\n"
    "            padding: 12px 22px;\n"
    "            font-weight: 700;\n"
    "            font-size: 15px;\n"
    "            border: none;\n"
    "            border-radius: 8px;\n"
    "            cursor: pointer;\n"
    "            min-height: 46px;\n"
    "            display: inline-flex;\n"
    "            align-items: center;\n"
    "            justify-content: center;\n"
    "            gap: 6px;\n"
    "            text-decoration: none;\n"
    "            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);\n"
    "            transition: transform 0.1s, filter 0.15s, box-shadow 0.15s;\n"
    "        }\n\n"
    "        .btn:hover:not(:disabled) {\n"
    "            filter: brightness(1.15);\n"
    "            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);\n"
    "        }",
    'F2: unified button spec')

c = apply(c,
    "        .btn-registry {\n            background-color: #3b82f6;\n            color: #fff;\n        }",
    "        .btn-registry {\n            background-color: #3b82f6;\n            color: #fff;\n        }\n\n"
    "        .btn-sailwave {\n            background-color: #8b5cf6;\n            color: #fff;\n        }",
    'F3: btn-sailwave class')

c = apply(c,
    "            <button class=\"btn btn-registry\" id=\"btn-refresh-sailwave\" style=\"background-color: #8b5cf6;\">\U0001f504 Refresh Sailwave</button>",
    "            <button class=\"btn btn-sailwave\" id=\"btn-refresh-sailwave\">\U0001f504 Refresh Sailwave</button>",
    'F4: refresh button class')
save(p, c)

# ---------- templates/index.html ----------
p = 'templates/index.html'
c = load(p)

c = apply(c,
    "            <h1>\u269a FLAG MACHINE</h1>\n            <span class=\"version-tag\">v1.0 Demo Dashboard</span>\n            <a href=\"/finishsheet\" style=\"margin-left: 30px; padding: 8px 16px; background-color: #10b981; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 14px;\">\U0001f4ca Finish Sheet</a>",
    "            <h1>\u269a FLAG MACHINE</h1>\n            <span class=\"version-tag\">v1.0 Demo Dashboard</span>",
    'I1: old finish sheet link removed')

c = apply(c,
    "            <button id=\"btn-end-race\" class=\"btn btn-blue\" style=\"background-color: #007acc; color: white;\">\U0001f3c1 End Race</button>",
    "            <button id=\"btn-end-race\" class=\"btn btn-endrace\">\U0001f3c1 End Race</button>",
    'I2: end race button class')

c = apply(c,
    "        <button id=\"btn-refresh-sailwave\" class=\"btn btn-purple\" style=\"background-color: #8b5cf6; color: white; margin-left: 10px;\">\U0001f504 Refresh Sailwave</button>",
    "        <button id=\"btn-refresh-sailwave\" class=\"btn btn-sailwave\">\U0001f504 Refresh Sailwave</button>\n"
    "        <a class=\"btn btn-finishsheet\" href=\"/finishsheet?station=1\">\U0001f4ca Finish Sheet 1</a>\n"
    "        <a class=\"btn btn-finishsheet\" href=\"/finishsheet?station=2\">\U0001f4ca Finish Sheet 2</a>",
    'I3: sailwave class + both finish sheet stations linked')
save(p, c)

# ---------- static/css/style.css ----------
p = 'static/css/style.css'
c = load(p)

c = apply(c,
    ".btn {\n    padding: 10px 20px;\n    font-weight: bold;\n    border: none;\n    border-radius: 6px;\n    cursor: pointer;\n    font-size: 14px;\n    transition: transform 0.1s;\n}",
    "/* Unified button spec - same metrics as the finish sheet pages */\n"
    ".btn {\n"
    "    padding: 12px 22px;\n"
    "    font-weight: 700;\n"
    "    font-size: 15px;\n"
    "    border: none;\n"
    "    border-radius: 8px;\n"
    "    cursor: pointer;\n"
    "    min-height: 46px;\n"
    "    display: inline-flex;\n"
    "    align-items: center;\n"
    "    justify-content: center;\n"
    "    gap: 6px;\n"
    "    text-decoration: none;\n"
    "    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);\n"
    "    transition: transform 0.1s, filter 0.15s, box-shadow 0.15s;\n"
    "}\n\n"
    ".btn:hover:not(:disabled) {\n"
    "    filter: brightness(1.15);\n"
    "    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);\n"
    "}",
    'S1: unified button spec')

c = apply(c,
    ".btn-gray { background-color: #475569; color: #fff; }",
    ".btn-gray { background-color: #475569; color: #fff; }\n"
    ".btn-endrace { background-color: #007acc; color: #fff; }\n"
    ".btn-sailwave { background-color: #8b5cf6; color: #fff; }\n"
    ".btn-finishsheet { background-color: #10b981; color: #fff; }",
    'S2: new button colors')
save(p, c)

print('ALL LAYOUT PATCHES APPLIED')
