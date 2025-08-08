from app import dao
from app import app
from flask import render_template
@app.route('/')
def index():
    events = dao.load_event()
    return render_template("index.html", events=events)


if __name__ == '__main__':
    app.run(debug=True)