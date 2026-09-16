from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    paper_title = db.Column(db.String(100), default="나의 하루신문")
    nickname = db.Column(db.String(50), default="주인공")
    zodiac_sign = db.Column(db.String(20), default="양자리")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Entry(db.Model):
    __tablename__ = 'entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_str = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    topic = db.Column(db.String(50), nullable=False)     # daily, mood, music, food, ootd, book, culture
    content = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.Text, default='{}')        # JSON (예: music title, artist)
    image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_extra(self):
        return json.loads(self.extra_data) if self.extra_data else {}

class Edition(db.Model):
    __tablename__ = 'editions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_str = db.Column(db.String(10), nullable=False)
    highlight_entry_id = db.Column(db.Integer, nullable=True)
    include_weather = db.Column(db.Boolean, default=False)
    include_horoscope = db.Column(db.Boolean, default=False)
    include_fortune = db.Column(db.Boolean, default=False)
    generated_data = db.Column(db.Text, default='{}')    # AI 기자단 생성 기사 JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_data(self):
        return json.loads(self.generated_data) if self.generated_data else {}