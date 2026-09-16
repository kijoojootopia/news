import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from models import db, User, Entry, Edition
from services import generate_newspaper_articles
# dd
app = Flask(__name__)
app.config['SECRET_KEY'] = 'haru-secret-key-15yr-cto'
# 현재 파일(app.py)이 있는 위치의 절대 경로를 계산하여 DB 연결
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'haru_news.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_app(app)

with app.app_context():
    db.create_all()

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

@app.route('/')
def index():
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if action == 'register':
            if User.query.filter_by(username=username).first():
                flash('이미 존재하는 아이디입니다.')
                return redirect(url_for('login'))
            paper_title = request.form.get('paper_title', '나의 하루신문')
            nickname = request.form.get('nickname', '주인공')
            zodiac = request.form.get('zodiac_sign', '양자리')
            user = User(username=username, paper_title=paper_title, nickname=nickname, zodiac_sign=zodiac)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                return redirect(url_for('dashboard'))
            flash('아이디 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    today_str = datetime.now().strftime('%Y-%m-%d')
    entries = Entry.query.filter_by(user_id=user.id, date_str=today_str).all()
    return render_template('dashboard.html', user=user, today=today_str, entries=entries)

@app.route('/entries', methods=['POST'])
def add_entry():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    topic = request.form.get('topic')
    content = request.form.get('content', '')
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1]
            fname = f"{user.id}_{int(datetime.now().timestamp())}{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(fname)))
            image_filename = fname

    extra = {}
    if topic == 'music':
        extra['title'] = request.form.get('music_title', '')
        extra['artist'] = request.form.get('music_artist', '')

    entry = Entry(
        user_id=user.id,
        date_str=today_str,
        topic=topic,
        content=content,
        extra_data=json.dumps(extra, ensure_ascii=False),
        image_path=image_filename
    )
    db.session.add(entry)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/publish', methods=['POST'])
def publish():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
        
    today_str = datetime.now().strftime('%Y-%m-%d')
    highlight_id = request.form.get('highlight_id', type=int)
    inc_horoscope = bool(request.form.get('include_horoscope'))
    inc_fortune = bool(request.form.get('include_fortune'))
    inc_weather = bool(request.form.get('include_weather'))
    
    entries = Entry.query.filter_by(user_id=user.id, date_str=today_str).all()
    highlight_entry = Entry.query.get(highlight_id) if highlight_id else (entries[0] if entries else None)
    other_entries = [e for e in entries if e.id != (highlight_entry.id if highlight_entry else None)]

    generated = generate_newspaper_articles(
        nickname=user.nickname,
        highlight_entry=highlight_entry,
        other_entries=other_entries,
        include_horoscope=inc_horoscope,
        zodiac_sign=user.zodiac_sign,
        include_fortune=inc_fortune
    )
    
    edition = Edition(
        user_id=user.id,
        date_str=today_str,
        highlight_entry_id=highlight_entry.id if highlight_entry else None,
        include_weather=inc_weather,
        include_horoscope=inc_horoscope,
        include_fortune=inc_fortune,
        generated_data=json.dumps(generated, ensure_ascii=False)
    )
    db.session.add(edition)
    db.session.commit()
    
    return redirect(url_for('view_newspaper', edition_id=edition.id))

@app.route('/newspaper/<int:edition_id>')
def view_newspaper(edition_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    edition = Edition.query.get_or_404(edition_id)
    highlight_entry = Entry.query.get(edition.highlight_entry_id) if edition.highlight_entry_id else None
    return render_template('newspaper.html', user=user, edition=edition, data=edition.get_data(), highlight=highlight_entry)

if __name__ == '__main__':
    app.run(debug=True, port=5000)