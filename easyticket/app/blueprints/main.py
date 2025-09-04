from flask import Blueprint, render_template
from app.dao.event_dao import *
from app.dao.ticket_dao import *
from app.dao.event_dao import *

main = Blueprint('main', __name__, template_folder='templates')

@main.route('/')
def index():
    events = get_all_events()
    events_type = get_all_event_types()
    return render_template("user/index.html",events=events,events_type=events_type)