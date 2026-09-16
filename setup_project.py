import os

files = {}

# 1. requirements.txt
files["requirements.txt"] = """Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.3
Pillow==10.4.0
python-dotenv==1.0.1
"""

# 2. models.py
files["models.py"] = '''from flask_sqlalchemy import SQLAlchemy
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
'''

# 3. services.py
files["services.py"] = '''import random
import json

ZODIAC_FORTUNES = {
    "양자리": "새로운 시도가 뜻밖의 영감을 가져다주는 날입니다.",
    "황소자리": "차분한 쉼표 속에서 하루의 따뜻한 여유를 만끽할 수 있습니다.",
    "쌍둥이자리": "다양한 대화 속에서 반짝이는 아이디어를 얻게 됩니다.",
    "게자리": "마음이 편안해지는 아늑한 순간이 기다리고 있습니다.",
    "사자자리": "당신의 당당한 매력이 주변을 화사하게 밝힙니다.",
    "처녀자리": "정돈된 일상에서 소소하지만 확실한 만족을 찾습니다.",
    "천칭자리": "조화로운 리듬 속에서 기분 좋은 만남이 기대됩니다.",
    "전갈자리": "깊이 몰입했던 일에서 기대 이상의 보람을 느낍니다.",
    "사수자리": "발걸음 닿는 곳마다 즐거운 모험과 발견이 따릅니다.",
    "염소자리": "꾸준히 쌓아 올린 시간들이 빛을 발하기 시작합니다.",
    "물병자리": "틀을 깨는 나만의 감각이 특별한 하루를 완성합니다.",
    "물고기자리": "따스한 상상력이 메마른 일상을 촉촉하게 적셔줍니다."
}

FORTUNE_COOKIES = [
    "작은 용기가 커다란 행운의 문을 엽니다.",
    "오늘 당신이 들은 음악 한 곡이 오랫동안 마음에 남을 것입니다.",
    "기대하지 않았던 골목에서 당신만의 명장면을 마주하게 됩니다.",
    "따뜻한 차 한 잔으로 마음의 온도를 1도 올려보세요.",
    "오늘 찍은 사진 속 미소는 가장 소중한 부적이 됩니다."
]

def generate_newspaper_articles(nickname, highlight_entry, other_entries, include_horoscope, zodiac_sign, include_fortune):
    # LLM API 확장을 고려한 Structured Mock Engine
    main_title = f"{nickname}의 특별한 하루, 역사에 기록되다"
    main_body = f"{nickname}은(는) 오늘 가장 인상 깊은 순간으로 다음을 꼽았다: '{highlight_entry.content if highlight_entry else '평온한 일상의 흐름'}'."
    
    gossip = f"취재진에 따르면 {nickname}은(는) 오늘 유난히 기분 좋은 에너지를 풍기며 주변의 이목을 집중시켰다는 후문이다."
    
    music_data = None
    records = []
    for e in other_entries:
        if e.topic == 'music':
            extra = e.get_extra()
            music_data = {
                "title": extra.get("title", "Unknown Title"),
                "artist": extra.get("artist", "Unknown Artist"),
                "comment": e.content
            }
        else:
            records.append({
                "topic": e.topic,
                "content": e.content,
                "image": e.image_path
            })
            
    horoscope_text = ZODIAC_FORTUNES.get(zodiac_sign, "오늘 하루도 반짝이는 빛이 함께합니다.") if include_horoscope else None
    fortune_text = random.choice(FORTUNE_COOKIES) if include_fortune else None

    return {
        "headline": main_title,
        "main_article": main_body,
        "gossip": gossip,
        "music": music_data,
        "records": records,
        "horoscope": horoscope_text,
        "fortune": fortune_text
    }
'''

# 4. app.py
files["app.py"] = '''import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from models import db, User, Entry, Edition
from services import generate_newspaper_articles

app = Flask(__name__)
app.config['SECRET_KEY'] = 'haru-secret-key-15yr-cto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///haru_news.db'
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
'''

# 5. static/css/style.css
files["static/css/style.css"] = """@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,800;1,400&family=Cinzel:wght@700&display=swap');

body {
    font-family: 'Pretendard', sans-serif;
    background-color: #F7F5F0;
    color: #2D2A26;
}

.font-serif-headline {
    font-family: 'Playfair Display', serif;
}

.font-cinzel {
    font-family: 'Cinzel', serif;
}

/* 감성 크림 신문 배경 질감 */
.paper-texture {
    background-color: #FAF8F5;
    box-shadow: inset 0 0 40px rgba(220, 210, 195, 0.4), 0 8px 24px rgba(0, 0, 0, 0.06);
    border: 1px solid #E6DEC9;
}

/* LP 바이닐 회전 인터랙션 */
.vinyl-record {
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: radial-gradient(circle, #333 15%, #111 16%, #222 30%, #111 45%, #222 60%, #111 75%, #050505 100%);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
    animation: spin 6s linear infinite;
    animation-play-state: paused;
}

.vinyl-record.playing,
.group:hover .vinyl-record {
    animation-play-state: running;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* 포춘쿠키 인터랙션 */
.fortune-paper {
    background: #FFFDF8;
    border-left: 3px dashed #E29578;
    font-family: 'Courier New', Courier, monospace;
}
"""

# 6. static/js/story_export.js
files["static/js/story_export.js"] = """document.addEventListener('DOMContentLoaded', () => {
    const exportBtn = document.getElementById('export-story-btn');
    if (!exportBtn) return;

    exportBtn.addEventListener('click', async () => {
        const target = document.getElementById('story-canvas');
        if (!target) return;

        exportBtn.disabled = true;
        const originalText = exportBtn.innerText;
        exportBtn.innerText = '저장 중...';

        try {
            // 화면 밖 스토리 캔버스를 임시 활성화
            target.style.display = 'block';

            const dataUrl = await htmlToImage.toPng(target, {
                width: 1080,
                height: 1920,
                pixelRatio: 1,
                quality: 0.95
            });

            target.style.display = 'none';

            // 이미지 자동 다운로드 트리거
            const link = document.createElement('a');
            link.download = `haru_story_${new Date().toISOString().slice(0,10)}.png`;
            link.href = dataUrl;
            link.click();
        } catch (err) {
            console.error('스토리 이미지 생성 실패:', err);
            alert('이미지 저장 중 문제가 발생했습니다.');
        } finally {
            exportBtn.disabled = false;
            exportBtn.innerText = originalText;
        }
    });
});
"""

# 7. templates/base.html
files["templates/base.html"] = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>하루신문 — 나의 하루를 뉴스로</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html-to-image/1.11.11/html-to-image.min.js"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body class="min-h-screen flex flex-col">
    <header class="border-b border-[#E6DEC9] bg-[#FAF8F5]/80 backdrop-blur py-4 px-6 flex justify-between items-center">
        <h1 class="font-cinzel text-xl font-bold tracking-wider text-[#3D3A35]">HARU NEWSPAPER</h1>
        {% if session.get('user_id') %}
            <div class="flex items-center gap-4 text-sm">
                <a href="{{ url_for('dashboard') }}" class="text-[#7A746B] hover:text-black">오늘의 조각 담기</a>
                <a href="{{ url_for('logout') }}" class="text-[#D96B6B] hover:underline">로그아웃</a>
            </div>
        {% endif %}
    </header>
    <main class="flex-1">
        {% block content %}{% endblock %}
    </main>
    <script src="{{ url_for('static', filename='js/story_export.js') }}"></script>
</body>
</html>
"""

# 8. templates/login.html
files["templates/login.html"] = """{% extends "base.html" %}
{% block content %}
<div class="max-w-md mx-auto mt-16 p-8 paper-texture rounded-lg">
    <h2 class="font-serif-headline text-2xl text-center mb-6 font-bold">당신의 하루가 뉴스가 되는 곳</h2>
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            <div class="mb-4 text-xs text-red-500 bg-red-50 p-2 rounded border border-red-200">
                {{ messages[0] }}
            </div>
        {% endif %}
    {% endwith %}
    
    <form method="POST" class="space-y-4">
        <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">아이디</label>
            <input type="text" name="username" required class="w-full px-3 py-2 border rounded border-[#D5CDBD] bg-white focus:outline-none focus:ring-1 focus:ring-[#8EA4B8]">
        </div>
        <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">비밀번호</label>
            <input type="password" name="password" required class="w-full px-3 py-2 border rounded border-[#D5CDBD] bg-white focus:outline-none focus:ring-1 focus:ring-[#8EA4B8]">
        </div>
        <div id="register-fields" class="space-y-3 pt-2 border-t border-dashed border-gray-300">
            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">신문 제호</label>
                <input type="text" name="paper_title" placeholder="지수의 하루신문" class="w-full px-3 py-2 border rounded border-[#D5CDBD] bg-white text-sm">
            </div>
            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">호칭 (주인공 이름)</label>
                <input type="text" name="nickname" placeholder="지수" class="w-full px-3 py-2 border rounded border-[#D5CDBD] bg-white text-sm">
            </div>
            <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1">별자리</label>
                <select name="zodiac_sign" class="w-full px-3 py-2 border rounded border-[#D5CDBD] bg-white text-sm">
                    <option value="양자리">양자리 (3.21~4.19)</option>
                    <option value="황소자리">황소자리 (4.20~5.20)</option>
                    <option value="쌍둥이자리">쌍둥이자리 (5.21~6.21)</option>
                    <option value="게자리">게자리 (6.22~7.22)</option>
                    <option value="사자자리">사자자리 (7.23~8.22)</option>
                    <option value="처녀자리">처녀자리 (8.23~9.22)</option>
                    <option value="천칭자리">천칭자리 (9.23~10.22)</option>
                    <option value="전갈자리">전갈자리 (10.23~11.22)</option>
                    <option value="사수자리">사수자리 (11.23~12.21)</option>
                    <option value="염소자리">염소자리 (12.22~1.19)</option>
                    <option value="물병자리">물병자리 (1.20~2.18)</option>
                    <option value="물고기자리">물고기자리 (2.19~3.20)</option>
                </select>
            </div>
        </div>
        <div class="flex gap-2 pt-2">
            <button type="submit" name="action" value="login" class="flex-1 bg-[#4A4E54] text-white py-2 rounded text-sm hover:bg-black transition">로그인</button>
            <button type="submit" name="action" value="register" class="flex-1 bg-[#8EA4B8] text-white py-2 rounded text-sm hover:bg-[#728A9E] transition">가입하기</button>
        </div>
    </form>
</div>
{% endblock %}
"""

# 9. templates/dashboard.html
files["templates/dashboard.html"] = """{% extends "base.html" %}
{% block content %}
<div class="max-w-4xl mx-auto py-8 px-4">
    <div class="flex justify-between items-end border-b pb-4 mb-6 border-[#D5CDBD]">
        <div>
            <h2 class="font-serif-headline text-3xl font-bold">{{ user.paper_title }}</h2>
            <p class="text-xs text-gray-500 mt-1">{{ today }}의 조각을 모으는 중</p>
        </div>
    </div>

    <!-- 1. 기록 작성 모듈 -->
    <div class="grid md:grid-cols-2 gap-6 mb-8">
        <!-- 일반 기록 카드 -->
        <div class="paper-texture p-5 rounded-lg border border-[#E6DEC9]">
            <h3 class="font-bold text-sm text-[#4A4E54] mb-3">일상·기분·기억 조각</h3>
            <form action="{{ url_for('add_entry') }}" method="POST" enctype="multipart/form-data" class="space-y-3">
                <select name="topic" class="w-full text-xs p-2 rounded border border-[#D5CDBD] bg-white">
                    <option value="daily">일상·기억하고 싶은 순간</option>
                    <option value="mood">오늘의 기분</option>
                    <option value="food">음식·카페</option>
                    <option value="ootd">OOTD</option>
                    <option value="book">책·마음에 남은 구절</option>
                    <option value="culture">공연·전시·영화</option>
                </select>
                <textarea name="content" required placeholder="무슨 일이 있었나요? 감상을 적어주세요." class="w-full text-xs p-2 border rounded border-[#D5CDBD] bg-white h-20"></textarea>
                <div class="flex items-center justify-between">
                    <input type="file" name="image" accept="image/*" class="text-xs text-gray-500">
                    <button type="submit" class="bg-[#4A4E54] text-white text-xs px-4 py-2 rounded hover:bg-black">조각 담기</button>
                </div>
            </form>
        </div>

        <!-- 음악 LP 기록 모듈 -->
        <div class="paper-texture p-5 rounded-lg border border-[#E6DEC9]">
            <div class="flex justify-between items-center mb-3">
                <h3 class="font-bold text-sm text-[#4A4E54]">오늘의 바이닐 레코드 (LP)</h3>
                <div class="vinyl-record"></div>
            </div>
            <form action="{{ url_for('add_entry') }}" method="POST" class="space-y-2">
                <input type="hidden" name="topic" value="music">
                <input type="text" name="music_title" required placeholder="곡명 (Song Title)" class="w-full text-xs p-2 border rounded border-[#D5CDBD] bg-white">
                <input type="text" name="music_artist" required placeholder="아티스트 (Artist)" class="w-full text-xs p-2 border rounded border-[#D5CDBD] bg-white">
                <input type="text" name="content" placeholder="이 음악을 들으며 어떤 생각을 했나요?" class="w-full text-xs p-2 border rounded border-[#D5CDBD] bg-white">
                <button type="submit" class="w-full bg-[#E29578] text-white text-xs py-2 rounded hover:bg-[#D07E60] transition">LP 트랙 등록</button>
            </form>
        </div>
    </div>

    <!-- 2. 오늘 모인 조각 목록 & 하이라이트 선택 -->
    <form action="{{ url_for('publish') }}" method="POST">
        <h3 class="font-bold text-sm text-[#4A4E54] mb-3">오늘 모인 조각 목록 (하이라이트 1개 선택)</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
            {% for entry in entries %}
                <label class="block p-3 paper-texture rounded border border-[#E6DEC9] cursor-pointer hover:border-black transition relative">
                    <input type="radio" name="highlight_id" value="{{ entry.id }}" class="absolute top-3 right-3" {% if loop.first %}checked{% endif %}>
                    <span class="inline-block text-[10px] uppercase font-bold text-gray-400 mb-1">[{{ entry.topic }}]</span>
                    <p class="text-xs text-gray-700 line-clamp-2">{{ entry.content }}</p>
                    {% if entry.topic == 'music' %}
                        <p class="text-[10px] text-[#E29578] mt-1 font-semibold">{{ entry.get_extra().title }} - {{ entry.get_extra().artist }}</p>
                    {% endif %}
                </label>
            {% else %}
                <div class="col-span-3 text-center py-6 text-xs text-gray-400 paper-texture rounded border border-dashed border-[#D5CDBD]">
                    아직 담긴 조각이 없습니다. 위에서 오늘의 이야기를 들려주세요.
                </div>
            {% endfor %}
        </div>

        <!-- 3. 자동 체크 코너 (날씨, 별자리, 포춘쿠키) -->
        <div class="paper-texture p-4 rounded-lg border border-[#E6DEC9] flex flex-wrap items-center justify-between gap-4 mb-6">
            <span class="text-xs font-bold text-gray-600">신문에 자동 포함할 코너:</span>
            <div class="flex items-center gap-4 text-xs">
                <label class="flex items-center gap-1.5 cursor-pointer">
                    <input type="checkbox" name="include_weather" value="1" checked class="rounded"> 오늘의 날씨
                </label>
                <label class="flex items-center gap-1.5 cursor-pointer">
                    <input type="checkbox" name="include_horoscope" value="1" checked class="rounded"> 별자리 운세 ({{ user.zodiac_sign }})
                </label>
                <label class="flex items-center gap-1.5 cursor-pointer">
                    <input type="checkbox" name="include_fortune" value="1" checked class="rounded"> 포춘쿠키 한 줄
                </label>
            </div>
        </div>

        <div class="text-center">
            <button type="submit" {% if not entries %}disabled{% endif %} class="bg-[#2D2A26] disabled:bg-gray-300 text-white px-8 py-3 rounded-full text-sm font-semibold tracking-wider hover:bg-black transition shadow-md">
                신문 발행하기
            </button>
        </div>
    </form>
</div>
{% endblock %}
"""

# 10. templates/newspaper.html
files["templates/newspaper.html"] = """{% extends "base.html" %}
{% block content %}
<div class="max-w-4xl mx-auto py-8 px-4">
    <!-- 상단 툴바 -->
    <div class="flex justify-between items-center mb-6">
        <a href="{{ url_for('dashboard') }}" class="text-xs text-gray-500 hover:text-black">← 다시 기록하기</a>
        <button id="export-story-btn" class="bg-[#E29578] text-white text-xs px-5 py-2.5 rounded-full font-bold shadow hover:bg-[#D07E60] transition">
            인스타그램 스토리로 저장 (9:16)
        </button>
    </div>

    <!-- 16:9 데스크톱 메인 신문 지면 -->
    <div class="paper-texture p-8 rounded-lg border-2 border-[#2D2A26] shadow-xl">
        <!-- 제호 헤더 -->
        <div class="text-center border-b-2 border-[#2D2A26] pb-4 mb-6">
            <div class="text-[10px] tracking-[0.3em] font-cinzel text-gray-500 uppercase">THE DAILY CHRONICLE</div>
            <h1 class="font-serif-headline text-4xl font-extrabold my-2 text-[#2D2A26]">{{ user.paper_title }}</h1>
            <div class="flex justify-between text-[11px] border-t border-[#2D2A26] pt-1 text-gray-600">
                <span>발행일: {{ edition.date_str }}</span>
                <span>주인공: {{ user.nickname }}</span>
                <span>VOL. 01</span>
            </div>
        </div>

        <!-- 1면 하이라이트 & 찌라시 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="md:col-span-2 border-r border-[#E6DEC9] pr-6">
                <span class="bg-[#2D2A26] text-white text-[10px] px-2 py-0.5 uppercase font-bold tracking-wider">TOP STORY</span>
                <h2 class="font-serif-headline text-2xl font-bold mt-2 mb-3">{{ data.headline }}</h2>
                {% if highlight and highlight.image_path %}
                    <img src="{{ url_for('static', filename='uploads/' + highlight.image_path) }}" class="w-full h-48 object-cover rounded mb-3 grayscale contrast-125 border border-black/20">
                {% endif %}
                <p class="text-xs leading-relaxed text-gray-800 text-justify">{{ data.main_article }}</p>
            </div>
            
            <div class="flex flex-col justify-between space-y-4">
                <div class="bg-[#F0EBE1] p-3 rounded border border-[#DDD5C5]">
                    <span class="text-[10px] font-bold text-[#D96B6B] block mb-1">데일리 찌라시</span>
                    <p class="text-[11px] leading-snug text-gray-700 italic">"{{ data.gossip }}"</p>
                </div>

                {% if data.fortune %}
                <div class="fortune-paper p-3 rounded text-[11px] text-gray-700">
                    <span class="text-[9px] font-bold tracking-widest text-[#E29578] uppercase block mb-1">FORTUNE COOKIE</span>
                    {{ data.fortune }}
                </div>
                {% endif %}

                {% if data.horoscope %}
                <div class="border-t border-dashed border-gray-300 pt-2 text-[11px] text-gray-600">
                    <span class="font-bold text-black">별자리 운세 ({{ user.zodiac_sign }}):</span>
                    <p class="mt-0.5">{{ data.horoscope }}</p>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- 하단: 음악 LP & 추가 기록 조각 그리드 -->
        <div class="border-t-2 border-[#2D2A26] pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            {% if data.music %}
            <div class="col-span-1 flex items-center gap-3 bg-[#F4EFE6] p-3 rounded border border-[#E0D8C7]">
                <div class="vinyl-record playing flex-shrink-0"></div>
                <div class="overflow-hidden">
                    <span class="text-[9px] uppercase font-bold text-gray-500">TODAY'S VINYL</span>
                    <div class="text-xs font-bold truncate">{{ data.music.title }}</div>
                    <div class="text-[10px] text-gray-600 truncate">{{ data.music.artist }}</div>
                    <div class="text-[9px] text-gray-500 italic mt-1 truncate">{{ data.music.comment }}</div>
                </div>
            </div>
            {% endif %}

            <div class="{% if data.music %}col-span-2{% else %}col-span-3{% endif %} grid grid-cols-2 gap-2">
                {% for r in data.records %}
                <div class="p-2 bg-white/70 border border-[#E6DEC9] rounded text-[10px]">
                    <span class="font-bold text-gray-500 uppercase">[{{ r.topic }}]</span>
                    <p class="text-gray-700 line-clamp-2 mt-0.5">{{ r.content }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</div>

<!-- 인스타그램 스토리 9:16 전용 히든 캔버스 (1080x1920) -->
<div id="story-canvas" style="display: none; width: 1080px; height: 1920px;" class="paper-texture p-[80px] relative font-sans">
    <!-- Safe Zone (상단 마진 170px 확보) -->
    <div style="margin-top: 170px;" class="border-4 border-[#2D2A26] p-12 h-[1450px] flex flex-col justify-between bg-[#FAF8F5]">
        <div>
            <!-- 헤더 -->
            <div class="text-center border-b-4 border-[#2D2A26] pb-6 mb-8">
                <div class="text-xl tracking-[0.4em] font-cinzel text-gray-500 uppercase">THE ANNUAL DAILY NEWS</div>
                <h1 class="font-serif-headline text-6xl font-black my-4 text-[#2D2A26]">{{ user.paper_title }}</h1>
                <div class="flex justify-between text-lg border-t-2 border-[#2D2A26] pt-2 text-gray-600">
                    <span>DATE: {{ edition.date_str }}</span>
                    <span>HERO: {{ user.nickname }}</span>
                    <span>SPECIAL EDITION</span>
                </div>
            </div>

            <!-- 하이라이트 -->
            <div class="mb-8">
                <span class="bg-[#2D2A26] text-white text-base px-3 py-1 uppercase font-bold tracking-wider">TOP HIGHLIGHT</span>
                <h2 class="font-serif-headline text-4xl font-bold mt-4 mb-4 leading-tight">{{ data.headline }}</h2>
                {% if highlight and highlight.image_path %}
                    <img src="{{ url_for('static', filename='uploads/' + highlight.image_path) }}" class="w-full h-[480px] object-cover rounded mb-4 grayscale contrast-125 border-2 border-black/30">
                {% endif %}
                <p class="text-xl leading-relaxed text-gray-800 text-justify">{{ data.main_article }}</p>
            </div>
        </div>

        <!-- 하단 컴팩트 모듈 (LP, 포춘, 별자리) -->
        <div class="border-t-4 border-[#2D2A26] pt-6 space-y-6">
            {% if data.music %}
            <div class="flex items-center gap-6 bg-[#F4EFE6] p-6 rounded-xl border border-[#E0D8C7]">
                <div style="width: 140px; height: 140px;" class="vinyl-record playing flex-shrink-0"></div>
                <div>
                    <span class="text-sm font-bold text-gray-500 uppercase">TODAY'S VINYL TRACK</span>
                    <div class="text-2xl font-black text-black">{{ data.music.title }}</div>
                    <div class="text-lg text-gray-600">{{ data.music.artist }}</div>
                    <div class="text-base text-gray-500 italic mt-1">"{{ data.music.comment }}"</div>
                </div>
            </div>
            {% endif %}

            <div class="grid grid-cols-2 gap-4">
                {% if data.fortune %}
                <div class="fortune-paper p-5 rounded-lg text-base text-gray-800">
                    <span class="text-xs font-bold text-[#E29578] uppercase block mb-1">FORTUNE COOKIE</span>
                    {{ data.fortune }}
                </div>
                {% endif %}

                {% if data.horoscope %}
                <div class="bg-[#F0EBE1] p-5 rounded-lg text-base text-gray-800">
                    <span class="text-xs font-bold text-gray-600 uppercase block mb-1">HOROSCOPE ({{ user.zodiac_sign }})</span>
                    {{ data.horoscope }}
                </div>
                {% endif %}
            </div>
        </div>
    </div>
    <!-- Safe Zone (하단 마진 170px 확보) -->
</div>
{% endblock %}
"""

# 파일 생성 실행
for path, content in files.items():
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())
    print(f"Created: {path}")

print("\n[완료] 프로젝트 스캐폴딩이 성공적으로 생성되었습니다.")
print("실행 방법:")
print("1. pip install -r requirements.txt")
print("2. python app.py")
print("3. 브라우저에서 http://127.0.0.1:5000 접속")