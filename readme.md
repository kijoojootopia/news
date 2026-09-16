# 📰 MyDailyGazette (나만의 하루 신문)

> "나의 하루가 특종이 되는 곳"  
> 하루 세 번 방문하여 완성하는 나만의 빈티지 신문 다이어리 웹 서비스
ㅗㅎㅀ ㄹ롷로
---ㅏㅓㅗ ㅏㅕㅕㅛㅑㅕㅛㅑ
ㅑ ㅕㅑㅐㅕㅑㅐ
]ㅕ ㅛㅑ

## 📌 1. 프로젝트 개요
* **서비스명**: MyDailyGazette (가칭)
* **개발 기간**: 2026.09 ~ 2026.10 (약 4주)
* **목표**: 일상 기록을 신문 기사 형식으로 재해석하여 시각적 즐거움과 아카이빙, 인스타그램 스토리 공유 경험 제공
* **주요 타겟**: 일상을 감성적으로 기록하고 공유하길 원하는 2030 세대

---

## ⏰ 2. 일일 서비스 흐름 (하루 3회 방문 트리거)
1. **아침 (조간)**: 오늘의 날씨 확인, 포춘쿠키 개봉 및 모닝 운세 확인
2. **오후 (취재)**: 오늘의 OOTD, 읽은 책 구절, 점심 메뉴 기록 (티켓/LP/메모 템플릿 입력)
3. **저녁 (석간 발행)**: 오늘 하루 하이라이트 입력 ➡️ AI 기자가 작성한 1면 특종 기사 및 인스타 스토리용 신문 이미지 다운로드

---

## 🎨 3. UI/UX 및 타이포그래피 (Font Specification)

본 프로젝트의 모든 본문, 위젯 텍스트, UI 폼에는 높은 가독성을 지닌 **Pretendard** 폰트를 표준 폰트로 사용합니다.

### 폰트 적용 가이드 (HTML / CSS)
신문 레이아웃의 기본 서체는 Pretendard를 사용하며, 신문 제호(Title)에 한해 세리프 폰트를 포인트로 혼용합니다.

```html
<!-- HTML 템플릿 헤더 삽입 (CDN) -->
<link rel="stylesheet" as="style" crossorigin href="[https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css](https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css)" />