from datetime import datetime, timedelta

from flask import Flask

from solve import g

app = Flask(__name__)

cache = {}


@app.route("/")
def index():
    cached = cache.get('index')
    if cached is None or datetime.utcnow() - cache[1] > timedelta(minutes=5):
        cache['index'] = g()
        cached = cache['index']
    return cached[0]


if __name__ == '__main__':
    app.run()
