from flask import Blueprint, render_template,request
from app.dao.event_dao import *

main = Blueprint('main', __name__, template_folder='templates')

@main.route('/')
def index():
    page = request.args.get('page',default=1, type=int)
    events = get_all_events(page)
    events_type = get_all_event_types()
    return render_template("user/index.html",events=events,events_type=events_type)