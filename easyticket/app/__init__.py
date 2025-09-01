from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
# from flask_login import LoginManager
# from datetime import datetime

app = Flask(__name__)
app.secret_key = 'HJGFGHF^&%^&&*^&*YUGHJGHJF^%&YYHB'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/ticketdb?charset=utf8mb4" % quote(
    'Admin@123')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app)
# login = LoginManager(app)

