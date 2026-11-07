# 다시 만나

반려동물을 잃어버린 보호자를 위한 구조동물 검색 데모입니다. React/Vite 화면과 FastAPI `/api/v1`, LangGraph 조건 분기·검증·수정 루프를 연결했습니다.

## 실행

Python 3.12 이상, uv, Node.js 18.17 이상(Vite 6 호환), npm이 필요합니다. 신규 환경은 지원되는 Node LTS를 권장합니다.

프로젝트 루트에서:

```powershell
uv sync --frozen
Copy-Item .env.example .env
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

다른 터미널에서:

```powershell
cd frontend
npm ci
npm run dev
```

- 화면: http://localhost:5173
- API 문서: http://127.0.0.1:8000/docs
- 상태: http://127.0.0.1:8000/api/v1/health
- `.env` 없이 실행해도 기본값은 샘플 모드입니다. `.env`와 `.data`, `.tools`, 가상환경은 Git에서 제외합니다.

## 두 가지 실행 모드

| 설정 | 로컬·공개 샘플 체험 | 실제 연동 |
| --- | --- | --- |
| `APP_MODE` | `local` | `live` |
| `STORAGE_BACKEND` | `sqlite` | `supabase` |
| 동물 데이터 | 명시적으로 생성한 가상 샘플 | 국가동물보호정보시스템 실제 응답 |
| 계획 | 규칙 기반, LLM 미호출 | OpenAI Responses API, `gpt-6-luna` |
| 저장 | 로컬 `.data/meet-again.db` | 지정 Supabase 스키마 |
| Discord | 발송하지 않음 | 동의·허용 목록·신청 조건 확인 후 발송 |

공개 샘플 체험 배포는 일회성 UI·워크플로우 확인용입니다. 샘플 환경의 SQLite 기록은 Render 재시작·재배포 시 사라질 수 있으며 영속 저장을 보장하지 않습니다. 실제 연동 모드는 Supabase를 필수로 요구하고 로컬 저장소로 자동 전환하지 않습니다.

## 체험 순서

1. 지역과 강아지/고양이 등 종류, 오늘 이전 기간을 선택합니다.
2. 털색에 `갈색`을 입력하고 검색합니다. 샘플은 선택 지역·종류·기간에 맞춰 생성됩니다.
3. 후보의 일치·불일치·미확인 단서와 상세를 확인합니다. 샘플 센터·동물은 실제 정보가 아닙니다.
4. `이번 검색의 검증·수정 이력`을 펼칩니다. 정상 검색에서는 수정 횟수가 0일 수 있습니다.
5. 조건을 저장하고 `저장한 검색`에서 다시 불러옵니다.
6. 필수 조건을 비워 검색하면 추가 입력을 요청합니다. 조건을 채워 재실행하면 같은 대화에 병합됩니다.
7. 명시적으로 확인한 특징은 `입력 특징을 확인하고 기억`으로 저장합니다. 다른 검색에서 `저장한 특징 사용`을 켜면 현재 입력이 우선합니다.

로그인은 없습니다. 브라우저에 저장한 무작위 데모 토큰을 서버에서 해시로 검증합니다. 다른 브라우저·기기에는 기록이 이어지지 않으며 브라우저 데이터 삭제 시 접근을 잃습니다. 기본 프로필 외 다중 동물 프로필은 API의 `profile_id`로 분리하며 UI 프로필 선택은 후속 범위입니다.

## 실제 API 연결

`.env.example`을 참고해 서버에 설정합니다. 비밀 키를 채팅·Git·프론트엔드 변수에 넣지 마세요.

| 환경변수 | 용도 |
| --- | --- |
| `OPENAI_API_KEY` | 모델 API 키. ChatGPT 구독과 별도 |
| `OPENAI_MODEL` | `gpt-6-luna` 유지, 해당 계정의 모델 사용 권한 확인 |
| `ANIMAL_API_KEY` | 공공데이터포털 서비스 활용 승인 후 받은 키, 일반/URL 인코딩 키 모두 처리 |
| `ANIMAL_API_BASE_URL` | 공식 v2 서비스 기본 주소 |
| `SUPABASE_URL` | `https://yaywavgjaquftvekuvsb.supabase.co` |
| `SUPABASE_SCHEMA` | `aio-03-p2-team1-demo` |
| `SUPABASE_SERVICE_ROLE_KEY` | 백엔드 전용, 프론트엔드에 전달하지 않음 |
| `KAKAO_REST_API_KEY` | 보호센터 주소 좌표 변환, 선택 사항 |
| `DISCORD_BOT_TOKEN` | Discord Bot 인증 토큰 |
| `DISCORD_ALLOWED_USER_IDS` | 사전 동의한 데모 수신자 ID, 쉼표 구분 |
| `CORS_ORIGINS` | 허용된 프론트엔드 origin, 쉼표 구분 |

Supabase 연결 도구의 권한 오류로 기존 원격 테이블은 확인하지 못했고 원격 변경도 하지 않았습니다. 먼저 기존 스키마를 확인한 뒤 `scripts/bootstrap_schema.sql`을 SQL Editor에서 검토·실행하세요. 이 파일은 서버 전용 문서 저장소의 초기화 SQL이며 마이그레이션 이력을 생성하지 않습니다. 정식 이력은 Supabase CLI로 별도 생성·관리해야 합니다.

Data API의 Exposed schemas에 `aio-03-p2-team1-demo`를 추가해야 합니다. 이 테이블은 RLS를 활성화하고 `anon`·`authenticated` 접근을 허용하지 않습니다. 서버 전용 키로 접근하며 FastAPI가 모든 요청에 데모 소유권 조건을 적용합니다. 기존 같은 이름 테이블이 있으면 자동 덮어쓰기를 기대하지 말고 호환성을 검토하세요.

`APP_MODE=live`, `STORAGE_BACKEND=supabase` 설정 후 서버를 다시 시작합니다. 키·스키마가 없으면 명시적으로 실패합니다. 실제 API·DB·모델·지도·Discord는 키가 없는 현재 환경에서 검증하지 않았습니다.

## 알림

- 주기 검색, Cron, 외부 공고 자동 감시는 없습니다.
- 사용자가 명시적으로 실행한 실제 검색 결과를 **같은 브라우저 소유자의** 저장 검색·활성 신청과 대조합니다.
- 저장 조건의 지역·종류·기간에 맞고, 추가 특징이 있다면 최소 한 단서가 맞는 후보를 Discord DM으로 보냅니다.
- 신청 시 저장한 기간을 그대로 사용합니다. 향후 날짜를 자동으로 늘리지 않습니다.
- 샘플 데이터는 절대로 발송하지 않습니다. 신청 확인 DM도 자동 발송하지 않습니다.
- Bot 토큰과 허용 목록에 수신자 ID를 설정하고 실제 Discord DM 수신을 확인해야 합니다. 채널 웹훅을 사용하지 않습니다.
- 같은 신청·공고는 한 번만 발송하고 검색당 최대 3건을 처리합니다. 신청 해제 시 이후 검색에서 발송하지 않습니다.
- `accepted`는 Discord의 메시지 생성 요청 수락이며 실제 사용자 열람을 뜻하지 않습니다.
- 메시지 POST 타임아웃은 중복 위험 때문에 자동 재시도하지 않습니다. `failed_or_unknown`을 확인하고 운영자가 수신 여부를 점검해야 합니다.
- 문자·브라우저 푸시는 미구현입니다. 이번 데모에서는 사용자가 선택한 Discord DM을 우선했습니다.

## 지도·조회 범위

카카오 REST 키가 있으면 상위 3개 후보의 보호센터 주소를 좌표로 변환합니다. `frontend/.env.local`에 `VITE_KAKAO_JS_KEY`를 설정하고 카카오 앱의 허용 도메인에 배포 주소를 등록하면 지도도 표시합니다. 브라우저용 키는 공개되므로 도메인 제한을 적용하세요.

좌표가 없어도 실제 공고의 주소·발견 장소를 카카오맵 검색으로 확인할 수 있습니다. 장소 검색은 검증된 정확한 구조 좌표가 아니며, 실시간 거리·경로 계산은 미구현입니다.

실제 검색은 시도 단위로 최대 3페이지(페이지당 50건)를 조회하고 상위 10건을 표시합니다. 전체 건수·페이지·누락 필드·부분 조회 여부를 반환합니다. 시군구 필터 UI는 후속 범위이며 API에 임의 시군구 코드가 오면 추가 확인을 요청합니다. 품종·색상·특징은 문자열 비교에 각각 3·2·2 가중치를 사용합니다. 점수는 동일 개체의 확률이 아닙니다.

## 테스트·평가

```powershell
uv run pytest -q
uv run python -m scripts.evaluate
cd frontend
npm run build
```

평가 원본은 `docs/evaluation.json`입니다. 7개 고정 합성 시나리오를 성찰 ON/OFF로 한 번씩 실행합니다. 실패해야 하는 인증·영구 장애에서 안전하게 종료하는 것도 기대 결과에 포함합니다. 일시적 타임아웃·중복·종류 불일치는 ON에서 복구하고 OFF에서는 검증 실패로 종료합니다. 실제 검색 정확도·LLM 성능·통계적으로 유의한 지연 비교를 측정한 결과가 아닙니다.

## 배포

Render에 별도 API 서비스와 Static Site를 사용합니다. 기존 다른 프로젝트 서비스는 변경하지 않습니다.

API:

- 저장소 루트 기준 Python 3.12
- Build: `pip install uv && uv sync --frozen --no-dev`
- Start: `.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health: `/api/v1/health`
- 실제 모드에서 Supabase·외부 키를 Render Environment에 설정

Static Site:

- Build: `npm ci --prefix frontend && npm run build --prefix frontend`
- Publish directory: `frontend/dist`
- `VITE_API_BASE_URL=https://<API주소>/api/v1`
- 현재 UI는 경로 기반 라우터 없이 한 화면에서 탭을 전환하므로 SPA Rewrite가 필수는 아닙니다. 경로 라우팅 추가 시 `/* → /index.html` Rewrite를 설정하세요.
- API의 `CORS_ORIGINS`에 실제 Static Site origin을 등록

Render 무료 서비스는 유휴 상태에서 정지할 수 있고 최초 요청이 느릴 수 있습니다. 구체적인 배포 결과·주소·제약은 `docs/deployment.md`에 기록합니다.

설계·상태·API 계약은 [docs/architecture.md](docs/architecture.md)를 참고하세요.

## 공식 참고 자료

- [구조동물 조회 서비스 v2](https://www.data.go.kr/data/15098931/openapi.do): 페이지 내 OpenAPI 스키마의 경로·필드 확인
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [Supabase 사용자 지정 스키마](https://supabase.com/docs/guides/api/using-custom-schemas)
- [카카오 Local API](https://developers.kakao.com/docs/ko/local/dev-guide)
- [Discord Create DM](https://docs.discord.com/developers/resources/user#create-dm)
- [Render Static Sites](https://render.com/docs/static-sites)
