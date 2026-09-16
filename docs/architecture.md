# 화면·폴더·데이터·API 설계

이 문서는 ZIP에 포함된 Flask v1의 실제 구현을 설명합니다. 인증·기록 수정은 서버 렌더링 폼을, 비동기 발행은 JSON API를 사용합니다.

## 화면 구성

| 화면 | 템플릿 | 주요 구성 |
| --- | --- | --- |
| 홈 | `home.html` | 신문 일러스트, 소개, 오늘 신문 채우기 |
| 가입 / 로그인 | `auth.html` | 아이디·비밀번호·기사 속 이름 |
| 오늘 대기실 | `desk.html` | 날짜 → 직접 기록 주제 카드 → 구분선 → 자동 코너 체크박스 → 누적 기록 → 하이라이트·발행 |
| 주제별 작성 | `entry.html` | 사진·촬영, 주제별 입력칸, 저장 |
| 발행 진행 | `desk.html`의 dialog | 리본 일러스트, 진행률, 주기적 상태 조회 |
| 신문 결과 | `edition.html` | 1면·단신·나머지 기사·자동 코너, 내보내기·공유 |
| 기사 편집 | `edit_edition.html` | 헤드라인·단신·각 기사 제목/본문 편집, 새 버전 저장 |
| 보관함 | `archive.html` | 월·텍스트 검색, 날짜별 최신 발행본, 이전 버전 |
| 설정 | `settings.html` | 기사 속 이름·신문명·시간대·지역·응원 팀 |
| 휴지통 | `trash.html` | 삭제한 기록·복원 |
| 링크 생성 완료 | `share_created.html` | 링크 복사, 공개 범위 안내 |
| 공개 신문 | `edition.html` | 한 발행본과 해당 사진만 읽기 전용 표시 |
| 오류 | `error.html` | 메시지, 돌아가기 |
| 공통 | `base.html`, `macros.html` | 내비게이션·푸터·알림, 일러스트·단계 표시·CSRF 입력 |

일러스트는 3×3 에셋 시트의 각 구역을 CSS 배경으로 표시합니다. UI는 자바스크립트 프레임워크 없이 Jinja·CSS·기본 JavaScript로 구현했습니다. 기본 폼은 서버에서 검증하고, 발행과 시스템 공유에는 JavaScript가 필요합니다.

## 직접 기록 주제

| ID | 입력 템플릿 | 기자 페르소나 |
| --- | --- | --- |
| `daily` | 오늘의 순간, 어떤 일이 있었나요?, 장소(선택) | 다정한 일상 기자 |
| `mood` | 오늘의 기분, 그렇게 느낀 이유 | 마음 관찰 기자 |
| `food` | 음식/카페 이름, 이야기, 장소(선택) | 호기심 많은 미식 기자 |
| `ootd` | 스타일, 옷 이야기, 포인트(선택) | 섬세한 스타일 기자 |
| `music` | 곡 이름, 아티스트, 감상·링크(선택) | 음악 칼럼니스트 |
| `book` | 책 이름, 나의 생각, 저자·구절(선택) | 사려 깊은 문학 기자 |
| `culture` | 작품/행사 이름, 감상, 장소(선택) | 감성적인 문화 평론가 |

사진은 모든 주제에서 선택입니다. 같은 주제·같은 날짜에 여러 기록이 가능합니다. 긴 입력칸은 2,000자, 한 줄 입력칸은 120자까지입니다. AI 모드의 단신은 하이라이트 기록을 바탕으로 별도의 단신 기자가 작성합니다.

## DB 구조

| 테이블 | 핵심 값 | 역할 |
| --- | --- | --- |
| `users` | id, username, password_hash, display_name, newspaper_name, timezone, city, team | 계정·개인 설정 |
| `entries` | id, user_id, date, topic, title, fields, photos, version, deleted | 주제별 원본 기록, 낙관적 버전 관리 |
| `media` | id, user_id, filename | 소유자별 사진 파일 위치 |
| `day_settings` | user_id + date, automatic | 날짜별 자동 코너 선택 |
| `publications` | id, user_id, request_key, status, progress, source, content, error | 발행 작업과 취재 데이터 스냅샷 |
| `revisions` | id, user_id + date + revision, content | 변경하지 않는 완성 발행본 |
| `shares` | id, user_id, revision_id, token_hash, revoked | 한 발행본을 가리키는 공개 링크 |

JSON은 TEXT 열에 저장합니다. UUID를 외부 ID로 사용하고 SQL은 파라미터 바인딩으로 실행합니다. 비밀번호는 Werkzeug 해시로, 공개 링크의 토큰은 SHA-256 해시로 저장합니다. 날짜는 `YYYY-MM-DD`, 서버 이벤트 시각은 UTC입니다.

## 폼·화면 경로

| 메서드 | 경로 | 기능 |
| --- | --- | --- |
| GET | `/` | 홈 |
| GET / POST | `/signup` | 가입 화면 / 계정 생성 |
| GET / POST | `/login` | 로그인 화면 / 로그인 |
| POST | `/logout` | 로그아웃 |
| GET | `/today?date=YYYY-MM-DD` | 그날 기록과 자동 코너 불러오기 |
| POST | `/day-options` | 자동 코너 선택 저장 |
| GET / POST | `/entries/new/<topic>?date=YYYY-MM-DD` | 주제별 작성 / 저장 |
| GET / POST | `/entries/<id>/edit` | 원본 기록 조회 / 수정 |
| POST | `/entries/<id>/delete` | 휴지통 이동 |
| POST | `/entries/<id>/restore` | 복원 |
| GET | `/trash` | 내 휴지통 |
| GET | `/media/<id>` | 내 사진 파일 |
| GET / POST | `/settings` | 설정 조회 / 수정 |
| GET | `/archive?month=YYYY-MM&q=검색어` | 날짜별 보관함 |
| GET | `/editions/<id>` | 발행본 보기 |
| GET / POST | `/editions/<id>/edit` | 기사 수정 화면 / 새 버전 생성 |
| GET | `/editions/<id>/export/png` | 1면 요약 PNG |
| GET | `/editions/<id>/export/pdf` | 전체 PDF |
| POST | `/editions/<id>/share` | 읽기 전용 링크 생성 |
| POST | `/shares/<id>/revoke` | 공유 링크 해제 |
| GET | `/s/<token>` | 공개 발행본 |
| GET | `/s/<token>/media/<id>` | 그 발행본에 포함된 사진만 제공 |

폼의 쓰기 요청에는 `csrf_token`이 필요합니다. 기록 저장은 `multipart/form-data`이며 사진 입력 이름은 `photos`와 `camera`입니다. 수정과 삭제는 기존 `version`을 전달합니다. 다른 탭에서 먼저 수정하면 HTTP 409로 알려줍니다.

## 비동기 발행 API

### POST `/api/v1/publications`

로그인 세션 쿠키, `Content-Type: application/json`, `X-CSRF-Token`, `Idempotency-Key` 헤더가 필요합니다. CSRF 값은 페이지의 `meta[name="csrf-token"]`에 있습니다. 요청 키는 영문·숫자·`_`·`-`로 된 8~100자 문자열입니다.

```json
{
  "date": "2026-09-16",
  "entry_ids": ["record-id-1", "record-id-2"],
  "highlight_id": "record-id-1",
  "automatic": ["weather", "cookie"]
}
```

조건:

- 모든 기록은 로그인한 사용자의 해당 날짜 기록이어야 합니다.
- `entry_ids`는 중복 없는 목록이며 하나 이상 필요합니다.
- `highlight_id`는 `entry_ids`에 있어야 합니다. 자동 코너만으로는 발행할 수 없습니다.
- 자동 코너 ID는 `weather`, `sports`, `fortune`, `cookie`입니다.
- 같은 사용자는 한 번에 작업 하나를 발행합니다.
- 같은 요청 키와 같은 내용은 기존 작업을 반환합니다. 내용을 바꿔 같은 키를 사용하면 409입니다. 실패 후 새 시도는 새로운 키를 사용합니다.

성공 응답: HTTP 202

```json
{"data": {"id": "publication-job-id"}}
```

### GET `/api/v1/publications/<id>`

본인 작업만 조회할 수 있습니다. 프런트엔드는 약 1.5초 간격으로 조회합니다.

```json
{
  "data": {
    "id": "publication-job-id",
    "status": "succeeded",
    "progress": 100,
    "error": null,
    "url": "/editions/revision-id?reveal=1"
  }
}
```

상태는 `queued`, `running`, `succeeded`, `failed`입니다. `url`은 성공했을 때만 존재합니다. 화면을 다시 열면 진행 중인 해당 날짜 작업을 DB에서 찾아 이어서 조회합니다. 진행률은 처리 단계 기준이며 실제 남은 시간을 뜻하지 않습니다.

공통 오류 형식:

```json
{"error": {"message": "포함된 기록 중 1면 하이라이트를 선택해주세요."}}
```

| 코드 | 의미 |
| --- | --- |
| 400 | CSRF 누락 / 만료 |
| 401 | API 요청의 로그인 필요 |
| 404 | 작업·기록 없음 또는 다른 계정 소유 |
| 409 | 중복 작업, 요청 키 충돌, 수정 충돌 |
| 413 | 업로드 총 용량 초과 |
| 422 | 입력값 오류 |
| 429 | 로그인·가입 시도 횟수 초과 |
| 503 | 실제 AI 모드인데 API 키 없음 |

## 생성과 저장

1. 발행 요청 시 선택한 기록·사진 ID·기자용 이름·날짜별 옵션을 복사합니다.
2. 작업 스레드가 주제별 기사와 단신, 자동 코너를 만듭니다.
3. 원본 기록의 버전·삭제 여부를 다시 확인합니다. 변경됐다면 실패로 끝내고 원본을 유지합니다.
4. 한 트랜잭션에서 새 발행 버전을 추가하고 작업을 성공으로 표시합니다.
5. 결과를 렌더링하고 보관함에 표시합니다.

기사 편집은 AI 요청 없이 새 버전을 추가합니다. 최신 버전이 아닌 신문에서 편집을 저장하면 충돌로 안내합니다. 이전 발행본과 공유 링크는 자동으로 바뀌지 않습니다.

## 확장 지점

- 주제 추가: `catalog.py`와 데모 문장 사전(`news.py`)에 추가하고 일러스트를 연결합니다.
- 자동 코너 공급자 추가: `news.py`의 `automatic_sections()`에 구현합니다. 미연동·오류 상태와 출처를 함께 저장합니다.
- 디자인 수정: 템플릿과 CSS를 수정합니다. API에서 HTML을 받지 않습니다.
- 운영 배포: 현재 프로세스 내부 큐를 외부 작업 큐로 교체하고 DB 마이그레이션·인증 운영 기능을 추가합니다. 이 버전은 다중 워커 실행을 가정하지 않습니다.
