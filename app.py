from flask import Flask
from flask import render_template

app = Flask(__name__)

def format_totals(totals):
    return """<table class="summary"><th><tr><td>Total</td><td>Next Milestone</td><td>Remaining</td></tr></th>
            <tr><td>{}</td><td>{}</td><td>{}</td></tr></table>""".format(totals["total"], totals["next"], totals["need"])

def format_optimization(optimization):
    line = "<h1>Countdown</h1>"
    if len(optimization) == 0:
        return line + "<h2>Do not even bother, reach your 750000 first</h2>";
    for o in optimization:
        line += "<hr>"
        line += "<h2>{} to reach {}</h2>".format(o["remaining"], o["milestone"])
        line += "<p>Total: {} including: ".format(o["total"])
        for p in sorted(o["shifts"].keys()):
            line += '<span class="entry">{}: <b>{}</b></span>'.format(p, o["shifts"][p])
        line += "</p>"

    return line


def format_as_html(data):
    print(data)
    body = """<html><head><style>
    .entry {
        display: inline-block;
        margin: 2px 4px;
        padding: 4px;
        background-color: #eee;
        border: 1px solid #ccc;
        border-radius: 8px;
    }
    .summary {
        border: 1px solid black;
        border-collapse: collapse;
    }
    .summary td {
        border: 1px solid black;
        padding: 5px;
    }
    </style></head>
    """
    body += '<h1>Current records</h1>'
    body += format_totals(data["totals"])
    body += '<p>'
    for name in sorted(data["records"].keys()):
        body += '<span class="entry">{}: <b>{}</b></span>'.format(name, data["records"][name])
    body += '</p>'
    body += format_optimization(data["optimizations"])
    return body + '</html>'

@app.route('/')
def index():
    from process import find_best, download_and_read_data
    return format_as_html(find_best(download_and_read_data()))

@app.route('/gen')
def get():
    return render_template('index.html')

@app.route('/data/<adjustment>/<at_least>/<generations>')
def data(adjustment, at_least, generations):
    from process import download_and_read_data, find_best_genetic
    result = find_best_genetic(download_and_read_data(), int(adjustment), int(at_least), int(generations))
    return result

