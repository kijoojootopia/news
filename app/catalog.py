"""입력 스키마, 일러스트 위치, 기자 역할을 한 곳에서 관리합니다."""

TOPICS = {
    "daily": {
        "name": "일상 · 순간",
        "art": 0,
        "reporter": "다정한 일상 기자",
        "hint": "오래 기억하고 싶은 작은 순간",
        "fields": [
            ("title", "오늘의 순간", "text", True),
            ("memo", "어떤 일이 있었나요?", "textarea", True),
            ("place", "장소", "text", False),
        ],
    },
    "mood": {
        "name": "오늘의 기분",
        "art": 1,
        "reporter": "마음 관찰 기자",
        "hint": "지금의 마음을 한 줄로",
        "fields": [
            ("title", "오늘의 기분", "text", True),
            ("memo", "그렇게 느낀 이유", "textarea", True),
        ],
    },
    "food": {
        "name": "음식 · 카페",
        "art": 2,
        "reporter": "호기심 많은 미식 기자",
        "hint": "맛있었던 것, 쉬어간 곳",
        "fields": [
            ("title", "음식 또는 카페 이름", "text", True),
            ("memo", "맛과 그 순간의 이야기", "textarea", True),
            ("place", "장소", "text", False),
        ],
    },
    "ootd": {
        "name": "오늘의 옷차림",
        "art": 3,
        "reporter": "섬세한 스타일 기자",
        "hint": "오늘 나다운 옷 한 벌",
        "fields": [
            ("title", "오늘의 스타일", "text", True),
            ("memo", "어떤 옷을 입었나요?", "textarea", True),
            ("point", "마음에 드는 포인트", "text", False),
        ],
    },
    "music": {
        "name": "오늘의 음악",
        "art": 4,
        "reporter": "음악 칼럼니스트",
        "hint": "하루에 배경음악을 더해요",
        "fields": [
            ("title", "곡 이름", "text", True),
            ("artist", "아티스트", "text", True),
            ("memo", "언제 들었고 어떤 느낌이었나요?", "textarea", False),
            ("link", "음악 링크", "url", False),
        ],
    },
    "book": {
        "name": "책 · 한 문장",
        "art": 5,
        "reporter": "사려 깊은 문학 기자",
        "hint": "마음에 접어둔 문장",
        "fields": [
            ("title", "책 이름", "text", True),
            ("author", "저자", "text", False),
            ("quote", "기억할 구절", "textarea", False),
            ("memo", "나의 생각", "textarea", True),
        ],
    },
    "culture": {
        "name": "공연 · 전시 · 영화",
        "art": 6,
        "reporter": "감성적인 문화 평론가",
        "hint": "티켓 뒤에 남은 이야기",
        "fields": [
            ("title", "작품 또는 행사 이름", "text", True),
            ("memo", "기억에 남은 장면과 감상", "textarea", True),
            ("place", "장소", "text", False),
        ],
    },
}
AUTOMATIC = {
    "weather": {
        "name": "오늘의 날씨",
        "description": "설정한 지역의 날씨 · 연동 설정 필요",
    },
    "sports": {"name": "응원 팀 소식", "description": "경기 API 준비 중 · 미연동 표시"},
    "fortune": {
        "name": "오늘의 운세",
        "description": "재미로 보는 문구 · 사주 계산 제외",
    },
    "cookie": {"name": "포춘쿠키", "description": "오늘을 위한 작은 문장"},
}
CITIES = {
    "서울": (37.57, 126.98),
    "부산": (35.18, 129.08),
    "대구": (35.87, 128.60),
    "인천": (37.46, 126.71),
    "제주": (33.50, 126.53),
    "광주": (35.16, 126.85),
    "대전": (36.35, 127.38),
}
