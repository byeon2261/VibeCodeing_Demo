# 다시 만나 — LangGraph 기반 구조동물 검색 서비스 프로젝트 프롬프트

당신은 우리 팀의 Python 백엔드·React 프론트엔드·LangGraph 에이전트 설계와 구현을 돕는 개발 파트너다. 아래 요구사항을 기준으로 실제 동작하는 데모 서비스를 단계적으로 구현하라. 설계 설명만 제공하지 말고, 확인된 범위의 코드 작성·실행·검증·배포 준비까지 진행하라.

최신 배포 기준: Redis 쿠키 인증 도입 후 Vercel의 `VITE_API_BASE_URL`은 `/api/v1`이다. 이전 항목의 Render 절대 URL 안내는 18번 이후 설정으로 대체한다. 로컬 구현과 실제 배포 상태는 구분하며, 21번에 마지막 원격 진단 결과와 배포에 필요한 조치를 기록한다.

## 1. 프로젝트 정보와 목표

- 프로젝트명: **다시 만나**
- 저장소: https://github.com/byeon2261/VibeCodeing_Demo
- 서비스 목적: 반려동물을 잃어버린 보호자가 구조·보호 중인 동물 공고를 검색하고, 유사 후보와 보호센터 연락처·위치를 확인하도록 돕는다.
- 데모 원칙: 화면은 단순하게 구성하되 실제 API 조회, 조건 적용, 도구 호출, 오류 수정, 결과 검증은 정확히 구현한다.

학습·구현 목표:

1. LangGraph로 다중 도구 선택과 결과에 따른 분기·순환 워크플로우를 설계한다.
2. 에이전트의 판단 오류를 감지하고 수정·재실행하는 자가 성찰 및 피드백 루프를 구현한다.
3. 단기 기억·장기 기억·컨텍스트 선택·요약 전략을 실제 요청 흐름에 연결한다.
4. 실시간 외부 API를 사용하는 정상·오류 시나리오를 검증한다.
5. 자가 성찰 적용 전후를 같은 기준으로 비교하고 사용자가 체험할 수 있도록 배포한다.

## 2. 기술 스택과 미확정 사항

확정된 기술:

- 프론트엔드: React.js
- 백엔드: Python
- 패키지 관리: uv
- 에이전트 워크플로우: LangGraph
- DB: Supabase
- 사용할 Supabase 프로젝트 URL: https://yaywavgjaquftvekuvsb.supabase.co
- Supabase 프로젝트 식별자(Project ref): `yaywavgjaquftvekuvsb`
- Supabase 사용 스키마: `aio-03-p2-team1-demo`
- 로그인: 데모에서는 로그인·회원가입 화면과 계정 인증 흐름을 구현하지 않는다.
- 백엔드 호스팅: Render
- 백엔드 프레임워크: FastAPI
- 백엔드 API 접두어: `/api/v1`
- 프론트엔드 개발 환경: Vite
- LLM 공급자: OpenAI(ChatGPT 모델을 OpenAI API로 사용)
- 모델 환경변수: `OPENAI_MODEL=gpt-6-luna`
- 지도 API: 카카오맵(Kakao Maps)
- 구조동물 API: 국가동물보호정보시스템 구조동물 조회 서비스 API
- 검색 실행: 사용자 요청 시 실행하며 주기적 검색·폴링·예약 검색은 구현하지 않는다.
- 알림: 사용자 신청에 따라 문자(SMS) 또는 Discord DM으로 발송한다. 브라우저 푸시는 가능한 환경에서 추가한다.
- Render 백엔드 실행 환경: 이미 정해져 있으므로 기존 설정을 확인해 사용한다.

다음은 제안이며 확정된 요구사항처럼 취급하지 않는다.

- 데모 화면: 검색 조건 입력, 후보 목록·상세, 저장 검색·알림, 실행 이력
- 프론트엔드 호스팅 추천: Render Static Site. 아직 확정된 호스팅 위치는 아니다.

기존 코드와 설정이 있다면 먼저 확인하고 따르라. DB·인증·라우터·배포 구성에 영향을 주는 아래 항목은 구현 전에 한 번에 묶어서 질문하라. 답변이 필요한 작업을 기다리는 동안 독립적인 UI·도메인 모델·도구 인터페이스·테스트 설계는 진행할 수 있다.

1. 지정된 `aio-03-p2-team1-demo` 스키마의 기존 테이블·마이그레이션·접근 정책과 연결 설정은 무엇인가?
2. 문자 발송 공급자와 발신번호 설정이 있는가? Discord Bot 설정과 수신자 연결 방식이 있는가? 두 채널 중 우선 구현할 채널을 확인하고 최소 한 채널의 실제 발송을 검증한다.
3. 주기적 조회 없이 신규 후보 알림을 발생시킬 외부 이벤트·웹훅이 있는가? 없다면 아래 데모 트리거 제안을 확인한다.
4. 기존 Render 서비스의 URL·시작 명령·환경변수 등 프로젝트 파일에서 확인할 수 없는 설정은 무엇인가?

로그인 생략, 스키마, FastAPI와 `/api/v1`, 공급자·모델·지도·구조동물 API, 주기적 검색 제외 여부는 확정 사항이므로 다시 선택하도록 질문하지 않는다. `OPENAI_MODEL` 값은 그대로 사용하되 실제 API 접근 가능 여부를 검증하고, 사용할 수 없으면 원인을 알린 뒤 대체 모델을 확인한다. ChatGPT 구독을 API 키나 API 사용 권한으로 간주하지 않는다.

API 키나 DB 비밀번호를 채팅에 그대로 요청하지 말고 필요한 환경변수 이름과 설정 위치를 안내한다. 미확정 기능은 미확정으로 표시하고, API와 배포 환경은 구현 시점의 공식 문서로 지원 여부·필드·제약을 확인한다.

## 3. 사용자 시나리오와 구현 범위

### 핵심 검색 흐름

1. 보호자가 잃어버린 동물의 정보를 입력한다.
2. 필수 조건과 누락·모순된 정보를 확인하고 필요하면 추가 질문한다.
3. 지역·기간·동물 종류를 기준으로 실제 구조·보호 공고 API를 조회한다.
4. 색상·품종·특징 등 확인 가능한 정보로 후보를 정렬한다.
5. 후보별 일치 근거와 불일치·미확인 정보를 함께 보여 준다.
6. 공고 상세, 보호센터 연락처, 구조 위치와 보호센터 위치를 안내한다.
7. 결과가 없으면 조회 범위와 이유를 설명하고 조건 변경 또는 알림 신청을 제안한다. 알림 발생 조건을 함께 안내한다.

최소 입력 항목 초안:

- 필수: 동물 종류, 검색 지역, 검색 기간
- 선택: 품종, 털색, 성별, 추정 나이·크기, 목줄·상처 등 특징, 실종 위치·일시
- 필수 항목이 없으면 API 호출 전에 질문한다. 동물 종류를 제한 없이 조회하는 기능이 필요하면 명시적인 ‘전체’ 선택으로 지원한다.
- 날짜 역전, 미래 날짜, 지원하지 않는 지역·종류 등을 검증한다.
- 지역은 실종 지역과 구조 지역이 다를 수 있음을 고려하고, 범위 확대는 사용자 동의를 받아 적용한다.

### 기억·저장·알림 흐름

- 검색 조건 저장 및 이전 검색 불러오기
- 확인된 동물 특징과 사용자 선호 저장
- 알림 신청·수신 채널 등록·해제
- 이벤트로 확인된 유사 후보의 중복 없는 알림 발송과 발송 상태 기록
- 검증·수정 이력과 자가 성찰 전후 평가 결과 기록

**주기적 검색은 구현하지 않는다.** 알림 신청만으로 외부 공고의 신규 등록을 감지할 수 있다고 가정하지 않는다. 공식 API의 이벤트·웹훅 지원 여부를 확인하고, 지원이 확인되지 않으면 자동 신규 공고 감지 기능을 약속하지 않는다.

알림 트리거는 아직 미확정이다. 외부 이벤트가 없을 때의 데모 제안은 사용자가 명시적으로 실행한 검색에서 확인한 후보를 기존 알림 신청 조건과 대조하거나, 접근이 제한된 데모용 명시적 이벤트로 발송 경로를 검증하는 방식이다. 테스트 이벤트는 실제 신규 공고와 구분하고 일반 사용자에게 임의 발송 권한을 노출하지 않는다. 신청 직후의 등록 확인 알림과 후보 발견 알림도 구분한다. 이 제안을 자동 감시 구현으로 표현하지 않는다.

문자와 Discord DM은 교체 가능한 발송 어댑터로 설계하고 수신자가 선택한 채널로 발송한다. 문자 공급자·발신번호·수신번호 또는 Discord Bot·수신자 ID·DM 허용 조건을 확인한다. Discord 채널 웹훅을 개인 DM 기능으로 대체하지 않는다. 수신 동의, 신청 해제, 발송 빈도 제한, 실패 기록, 제한된 재시도를 지원한다. 외부 공급자의 요청 수락과 실제 전달 완료를 구분한다.

브라우저 푸시는 추가 범위로 검토한다. 구현 시 HTTPS, Service Worker, Push 구독, 서버 발송 설정을 확인하고 사용자의 명시적 동작으로 권한을 요청한다. 미지원·권한 거부 환경에서는 기본 문자/DM 경로를 유지한다. 화면 내부 메시지나 알림 권한 요청만으로 푸시 구현을 완료했다고 표시하지 않는다.

지도에는 구조 위치와 보호센터 위치를 구분해서 표시한다. 좌표가 없으면 주소를 보여 주고 좌표 변환 여부를 명시한다. 전화는 실제 번호에 대한 `tel:` 링크로 제공한다. 길찾기·이동 거리·소요 시간은 지도 API 지원과 팀 우선순위를 확인한 뒤 추가한다. 이동 정보를 구현한다면 계산 시각과 이동 수단을 표시하고, 실시간 교통 데이터를 사용하지 않은 값을 실시간으로 표현하지 않는다.

## 4. 외부 도구 설계

최소한 아래 기능을 독립적인 도구 인터페이스로 구성한다.

| 도구 | 입력 | 출력·검증 사항 |
| --- | --- | --- |
| 구조·보호 동물 공고 검색 | 지역, 기간, 동물 종류, 페이지 조건 | 공고 식별자, 검색 결과, 페이지·전체 건수, 출처, 조회 시각 |
| 공고 상세 조회 | 공고 식별자 | 동물 특징, 상태, 구조 일시·위치, 보호센터 참조 |
| 보호센터 조회 | 센터 식별자 또는 공식 조회 조건 | 센터명, 연락처, 주소, 좌표 또는 좌표 부재 |
| 위치 확인 | 구조·센터 주소 또는 좌표 | 지도 표시 정보, 좌표 출처, 변환 실패 여부 |

구조동물 데이터는 **국가동물보호정보시스템 구조동물 조회 서비스 API**, 지도는 **카카오맵 API**를 사용한다. 공식 제공 기관, 인증 방식, 서비스 URL, 최신 명세와 이용 조건을 확인한 뒤 연동한다. 별도의 상세 조회·보호센터 엔드포인트가 있는지 확인하고, 없다면 실제 응답 필드로 가능한 기능을 구성한다. 존재하지 않는 엔드포인트를 만들지 않는다. 위 도구가 각각 다른 외부 API일 필요는 없지만 호출 목적·입출력·실패 처리는 분리한다.

공통 규칙:

- 사용자 입력과 API 코드 값 사이의 매핑을 관리한다.
- 타임아웃, 인증 오류, 호출 제한, 서버 오류, 빈 결과, 필드 누락을 구분한다.
- 빈 검색 결과와 호출 실패를 같은 결과로 처리하지 않는다.
- 페이지 일부만 조회했다면 검색 범위를 명시하고 전체를 검색했다고 표현하지 않는다.
- 외부 응답은 정규화·검증한 뒤 그래프 상태와 UI에 전달한다.
- 각 결과에 출처, 조회 시각, 공고 기준 시점·상태를 보존한다.
- 도구 이름·필수 인자·호출 가능 횟수를 제한하고 모델이 임의 URL이나 SQL을 실행하지 않도록 한다.

## 5. LangGraph 워크플로우

다음 흐름을 출발점으로 실제 노드·조건부 엣지·종료 조건을 구현한다.

```text
START
  → 요청 분석 및 입력 검증
  → [정보 부족] 추가 질문 → END(awaiting_input)
  → [정보 충분] 관련 기억 조회 및 컨텍스트 구성
  → 도구 선택 및 실행 계획
  → 도구 실행
  → 결과 정규화 및 후보 정렬
  → 규칙 기반 검증
  → [성찰 활성화] 자가 성찰
  → [수정 가능] 수정 전략 선택 → 도구 선택/실행 또는 후보 재평가
  → [검증 통과] 결과 생성 및 최종 검증
  → 확인된 기억·실행 이력 저장
  → END(completed)

재시도 한도 초과·복구 불가 오류 → 근거 있는 실패/부분 결과 → END(failed/partial)
조건 변경에 사용자 확인 필요 → 추가 질문 → END(awaiting_input)
```

도구 선택은 실제 상태에 따라 달라져야 한다. 예를 들어 입력이 부족하면 질문하고, 검색 결과에 센터 정보가 없으면 센터 도구를 호출하고, 위치 정보가 필요하면 위치 도구를 선택한다. 오류 유형과 도구 결과를 보고 다음 노드를 결정하며, 선택 근거와 실행 흔적을 기록한다.

추가 질문 후에는 동일 사용자·세션의 기존 조건과 새 답변을 병합해 이어서 처리한다. 프로세스가 재시작되었을 때 단기 기억을 복원할 수 있도록 체크포인트 저장 방식을 정한다.

### 자가 성찰과 수정 규칙

감지 대상:

- 요청 지역·기간·종류와 후보의 불일치
- 필요한 도구를 호출하지 않은 상태에서 답변 생성
- 근거가 없는 동물 특징·보호센터 정보·연락처 생성
- 오래된 결과의 현재 정보 오인
- 페이지 누락, 응답 필드 누락, 중복 후보
- 잘못된 도구 인자, 반복되는 동일 호출, 순환 종료 실패

수정 전략 예:

- 인자 매핑 오류 → 공식 코드 값으로 수정 후 재조회
- 일시적 장애 → 제한된 횟수로 백오프 재시도
- 상세 정보 누락 → 상세·센터 도구 추가 호출
- 순위 오류 → 필터·정렬 규칙 재적용
- 조건 충돌·검색 범위 변경 필요 → 사용자에게 확인
- 인증 오류·사용 불가 API → 재시도 중단 및 원인 안내

수정 후 동일 검증을 다시 수행한다. 입력 조건을 조용히 완화하거나 데이터를 만들어 성공으로 처리하지 않는다. 도구별 재시도 횟수, 성찰 반복 한도, 전체 호출·시간 예산을 각각 설정하고 사용량을 기록한다. 초기값은 제안한 뒤 설정값으로 관리한다.

성찰 기록에는 오류 분류, 근거 데이터, 적용한 수정, 재검증 결과를 구조화해 남긴다. 모델의 비공개 사고 과정을 저장하도록 요구하지 않는다.

## 6. 상태·기억·컨텍스트 설계

구현 전 상태 필드마다 **이름·의미·자료형·초기값·읽는 노드·갱신하는 노드·영속 저장 여부**를 표로 작성한다. 다음 항목은 필드 설계의 출발점이며 필요에 따라 분리한다.

| 구분 | 포함할 정보 |
| --- | --- |
| 식별자 | 실행 ID, 사용자 ID, 세션/스레드 ID |
| 요청 | 메시지, 정규화한 검색 조건, 누락 항목, 사용자 확인 상태 |
| 계획·실행 | 선택 도구, 도구 인자, 호출 결과, 출처·조회 시각 |
| 후보 | 원본 공고 식별자, 특징, 순위 점수, 일치·불일치·미확인 근거 |
| 검증·성찰 | 검증 오류, 오류 횟수, 반복 횟수, 수정 전략, 재시도 이력 |
| 기억·컨텍스트 | 조회된 기억, 요약, 컨텍스트 예산, 요약 버전 |
| 종료 | 실행 상태, 부분 결과 여부, 종료 이유, 사용자 응답 |

### 기억의 적용 원칙

- 그래프 상태: 현재 실행에서 노드 사이에 전달할 정보
- 단기 기억: 같은 대화의 조건, 추가 질문과 답변, 직전 결과
- 장기 기억: 이후 대화에서도 사용할 사용자가 확인한 동물 특징·선호·저장 검색 기록
- 동물 특징은 사용자·동물 프로필 단위로 구분해 여러 동물이 섞이지 않게 한다.
- 적용 순서는 **현재 요청의 명시 조건 → 같은 세션의 확인된 조건 → 확인된 장기 기억 → 기본값**으로 한다.
- 예: 과거 ‘갈색’ 기록이 있어도 현재 요청에서 다른 동물을 찾는다고 하면 과거 특징을 자동 적용하지 않는다.
- 모델이 추정한 특징은 확인된 사실로 장기 저장하지 않는다.
- 저장·조회·수정·삭제 시점과 사용자 동의 방식을 정한다.
- 과거 공고·보호 상태는 검색 이력으로 취급하고 최신 확인이 필요한 정보는 재조회한다.

### 컨텍스트와 요약

- 현재 요청에 필요한 메시지, 관련 기억, 상위 후보, 도구 근거만 선택한다.
- 원본 API 전체 응답을 매번 모델에 전달하지 않는다.
- 토큰 예산과 요약 임계값을 설정하고 요약 발생 여부를 기록한다.
- 요약에는 확정 조건, 제외 조건, 미해결 질문, 결정사항, 근거 식별자·시각을 보존한다.
- API 키·불필요한 개인정보를 모델 입력과 요약에서 제외한다.
- 점수 계산·날짜 필터처럼 정확성이 필요한 처리는 구조화된 원본 데이터를 사용한다.

## 7. 후보 정렬과 결과 정확성

- 지역·기간·동물 종류의 필터 기준을 먼저 정의한다.
- 색상·품종·특징 등 선택 정보는 데이터 품질에 맞춰 점수화한다.
- 누락된 필드는 불일치와 구분하고, 정규화·가중치·동점 처리 규칙을 문서화한다.
- LLM은 특징 해석과 설명을 보조할 수 있지만 공고 식별자·연락처·날짜를 생성하지 않는다.
- 유사도 점수는 동일 동물일 확률로 표현하지 않는다.
- 후보는 ‘일치 확정’이 아닌 ‘확인할 유사 후보’로 안내하고 보호센터 확인 절차를 제공한다.
- 결과가 없더라도 ‘보호 중인 동물이 없다’고 단정하지 않고 실제 조회한 조건·시각·범위를 보여 준다.

## 8. Supabase 데이터와 백엔드 API 설계

사용할 Supabase 프로젝트는 `https://yaywavgjaquftvekuvsb.supabase.co`로 확정되어 있다. 연결 설정의 `SUPABASE_URL`에 이 URL을 사용하고, 새 프로젝트 생성이나 프로젝트 선택을 다시 요청하지 않는다. URL 지정만으로 연결·접근 권한이 확인된 것으로 간주하지 말고, 구현 시 실제 연결을 검증한다.

사용 스키마는 `aio-03-p2-team1-demo`로 확정되어 있다. `SUPABASE_SCHEMA=aio-03-p2-team1-demo`로 관리하고 모든 프로젝트 테이블·조회·마이그레이션이 이 스키마를 명시적으로 사용하게 한다. 하이픈이 있는 SQL 식별자는 `"aio-03-p2-team1-demo"`처럼 큰따옴표로 감싼다. 임의로 밑줄 이름으로 바꾸거나 `public`에 프로젝트 테이블을 생성하지 않는다. Data API를 사용한다면 해당 스키마의 노출·권한 설정을 확인한다.

로그인은 생략하되 브라우저별 데모 데이터를 구분한다. 서버가 발급한 추측하기 어려운 데모 세션 토큰을 이용하고, 클라이언트가 임의로 전달한 사용자 ID만으로 접근을 허용하지 않는다. 장기 기억과 저장 검색은 해당 데모 식별자에 연결하며 브라우저 데이터 삭제·다른 기기 사용 시 복원되지 않는 한계를 안내한다. DB 접근은 백엔드를 통해 처리하고 데모 토큰의 소유권 검사를 적용한다. 이 방식을 정식 계정 인증으로 표현하지 않는다.

백엔드 프레임워크는 FastAPI, API 접두어는 `/api/v1`로 확정한다. 기존 스키마와 라우터를 확인한 뒤 구체적인 테이블·마이그레이션·API 계약을 정한다. 다음 데이터 영역을 검토한다.

- 사용자·동물 프로필과 확인된 기억
- 세션·그래프 체크포인트·요약
- 저장 검색 조건과 알림 신청·해제 상태, 수신 채널·수신 대상
- 실행·도구 호출·검증·수정 이력
- 후보 이벤트·알림 발송 상태·실패 사유·중복 방지 키, 선택적 푸시 구독
- 평가 시나리오와 실행별 측정 결과

알림은 신청·공고·이벤트 종류·채널 등을 기준으로 중복을 방지한다. 이벤트 중복 수신이나 발송 재시도에도 중복 알림이 생기지 않도록 멱등성을 확보한다. 이미 본 과거 공고를 신규 후보로 재알림하지 않도록 기준 시점을 정의한다. 수신번호·Discord ID·푸시 구독 정보는 모델 컨텍스트와 공개 로그에서 제외한다.

제안할 API 기능:

- 검색 요청 및 추가 정보 응답
- 실행 상태·결과·검증 이력 조회
- 공고·보호센터 상세 조회
- 저장 검색 생성·목록·수정·삭제
- 알림 신청·해제, 수신 채널 설정, 발송 이력 조회
- 확정된 트리거에 따른 내부 이벤트 처리와 선택적 브라우저 푸시 구독·해제
- 사용자 기억 조회·수정·삭제
- 서버 상태 확인

각 API의 메서드·경로·요청/응답 모델·오류 코드·인증·소유권 검사를 문서화한다. 장시간 요청을 동기 응답으로 처리할지 실행 ID로 조회할지 데모 규모에 맞게 결정한다.

사용자별 데이터 접근을 격리하고 노출 테이블의 RLS·권한을 검토한다. Supabase 관리자 키와 외부 API 키는 서버 환경변수로만 관리하고 프론트엔드 번들·로그·저장소에 포함하지 않는다. 인증을 생략한 데모에서도 클라이언트가 전달한 임의 사용자 ID만으로 타인 데이터에 접근할 수 없게 한다.

## 9. 최소 화면

1. **검색:** 지역·기간·동물 종류·특징 입력, 누락 조건 확인, 실행 상태
2. **결과·상세:** 후보 목록, 일치 근거, 공고 출처·시각·보호 상태, 센터 연락처, 위치
3. **저장 검색·알림:** 이전 조건 불러오기, 알림 신청·해제, 문자/Discord DM 선택, 발송 상태, 지원 시 브라우저 푸시
4. **실행 이력:** 도구 호출, 오류·수정 요약, 최종 상태, 성찰 활성화 여부

로딩, 추가 질문, 빈 결과, 외부 API 오류, 부분 결과를 구분한다. 사용자는 내부 그래프 지식 없이 검색할 수 있어야 한다. 학습용 실행 이력은 별도 영역에서 확인하게 한다.

## 10. 검증과 성찰 전후 평가

같은 시나리오·조건·모델 설정·후보 정렬 기준에서 성찰 비활성화와 활성화를 비교한다. 두 모드 모두 기본 입력 검증·보안·종료 제한은 유지하고 성찰·수정 루프만 비교 변수로 둔다.

실제 API 연동 검증과 재현 가능한 비교 평가를 구분한다. 실제 조회 결과는 시점에 따라 변하므로 비교 평가는 같은 시점에 수집한 비식별 응답 스냅샷 또는 고정된 테스트 응답을 재사용한다. 실시간 호출 결과와 테스트 데이터를 구분해 표시한다.

최소 시나리오:

- 정상 조건 검색 및 후보·보호센터·위치 확인
- 필수 정보 누락 → 추가 질문 → 조건 병합 후 검색
- 잘못된 날짜·지역 코드 또는 도구 인자 → 감지·수정
- 정상적인 빈 결과
- 타임아웃·호출 제한·인증 오류·필드 누락
- 일부 페이지만 조회된 결과와 중복 공고
- 과거 기억과 현재 요청의 충돌
- 오래된 공고 정보의 재확인
- 잘못된 후보 정렬 또는 근거 없는 결과의 감지
- 반복 한도 도달 시 종료
- 장문 대화 요약 후 필수 조건 보존
- 사용자 요청에 따른 저장 검색 재조회와 이벤트 기반 알림의 중복 방지
- 문자 또는 Discord DM의 실제 발송, 수신 거부·발송 실패·신청 해제 처리
- 주기적 조회 없이 확정된 이벤트에서만 알림이 발생하는지 확인
- 브라우저 푸시 구현 시 권한 허용·거부·구독 해제·실제 수신 확인
- 다른 사용자의 검색·기억·알림 접근 차단

주요 지표:

| 지표 | 측정 기준 |
| --- | --- |
| 작업 성공률 | 사전 정의한 시나리오 완료 조건을 만족한 비율 |
| 조건 위반률 | 필수 조건에 어긋나는 최종 결과의 비율 |
| 수정 성공률 | 수정 가능한 오류를 감지하고 정상 상태로 복구한 비율 |
| 근거 충실도 | 결과의 주요 사실이 도구 응답과 연결되는 비율 |
| 후보 품질 | 정답 후보가 있는 검증 데이터의 Recall@K 또는 순위 지표 |
| 실행 비용 | 도구 호출 수, 성찰 반복 수, 토큰 사용량·비용 추정 |
| 지연 시간 | 전체 실행 시간과 주요 단계별 시간 |
| 종료 준수 | 호출·반복·시간 한도를 지켰는지 여부 |

지표별 분모·판정 기준·표본 수를 정의한다. 정답 데이터가 없으면 임의로 검색 정확도를 산출하지 않는다. 성찰로 품질이 좋아졌는지와 비용·지연 증가를 함께 기록하고 측정하지 않은 수치를 작성하지 않는다.

## 11. 배포와 산출물

- uv 기반 의존성과 잠금 파일을 관리하고 로컬 실행 명령을 제공한다.
- 환경변수 예시 파일에는 이름·설명·예시만 넣는다.
- Render에서 Python 서버 시작 명령, 포트 바인딩, 헬스 체크, CORS를 설정한다.
- 이미 정해진 Render 실행 환경을 우선 사용하고 예약 검색용 Cron·스케줄러를 추가하지 않는다.
- 이벤트 기반 알림 발송의 중복 방지·실패 기록을 검증한다. 요청 처리 이후에도 발송을 보장해야 한다면 영속 발송 작업과 기존 실행 환경에 맞는 처리 방식을 설계한다.
- Render의 임시 파일 시스템에 영속 기억·알림을 의존하지 않는다.
- 프론트엔드 호스팅은 **Render Static Site**를 추천한다. React/Vite SPA를 정적으로 배포하고 백엔드와 같은 플랫폼에서 관리할 수 있어 데모 운영이 단순하다. 추천안이며 실제 자원 생성 전 대상 설정을 확정한다.
- 프론트엔드 디렉터리를 기준으로 `npm ci && npm run build`, 게시 디렉터리 `dist`, 클라이언트 라우팅을 위한 `/* → /index.html` Rewrite를 설정한다. 프론트엔드 패키지는 npm과 잠금 파일로, Python 패키지는 uv로 관리한다.
- `VITE_API_BASE_URL`에는 공개 백엔드 HTTPS 주소와 `/api/v1`을 포함하고 경로 중복을 방지한다. FastAPI CORS에는 프론트엔드의 실제 origin을 등록한다. 카카오맵 허용 도메인도 로컬·배포 주소에 맞춰 설정한다.
- `VITE_` 변수는 브라우저에 공개됨을 전제로 한다. OpenAI·Supabase 관리자·문자·Discord Bot 비밀 키는 백엔드에만 둔다. 카카오맵 브라우저용 키는 허용 도메인 제한을 적용한다.
- 호스팅 설정 참고: https://render.com/docs/static-sites 및 https://vite.dev/guide/static-deploy
- 배포 전 DB 변경·외부 자원 생성의 영향과 필요한 설정을 정리한다. 배포 권한이 있으면 진행하고 권한·키가 없으면 필요한 항목과 현재 차단 지점을 명확히 기록한다.
- 배포 후 검색 → 결과 → 센터 확인 → 검색 저장 → 알림 신청 → 확정된 이벤트 → 문자/DM 수신 흐름을 실제 환경에서 확인한다.

필수 산출물:

1. 실행 가능한 프론트엔드·백엔드 코드
2. LangGraph 구조도와 분기·순환·종료 조건
3. 상태·기억·컨텍스트·요약 설계표
4. 외부 API·도구 명세와 백엔드 API 계약
5. DB 스키마·마이그레이션과 접근 정책
6. 핵심 흐름·오류 복구·데이터 격리에 대한 테스트
7. 성찰 전후 평가 데이터와 결과 보고서
8. README: 설치·실행·환경변수·배포·데모 시나리오·제약
9. 배포 주소 및 실제 확인 결과, 미완료 항목

## 12. 작업 진행 방식과 완료 기준

먼저 저장소의 기존 파일·규칙을 확인하고, 구현된 내용과 새로 필요한 내용을 구분하라. 이후 기존 DB 설정·알림 트리거·발송 설정 등 남은 확인 질문과 핵심 설계 초안을 제시하라. 확정된 프로젝트 목적·기술 스택·스키마·로그인 생략·API 접두어를 반복해서 질문하지 않는다.

구현 순서:

1. 외부 API 사용 가능 여부 확인, 요구사항·미확정 사항 정리
2. 상태·기억·도구·API·DB 계약 설계
3. 실제 API로 검색부터 상세 확인까지 기본 경로 구현
4. LangGraph 조건 분기·자가 성찰·수정·종료 구현
5. 기억·요약·검색 저장·이벤트 기반 알림 연결, 가능하면 브라우저 푸시 추가
6. 단순한 React 화면으로 핵심 흐름 연결
7. 정상·오류 검증과 성찰 전후 평가
8. 배포·실환경 확인·문서 정리

각 단계에서 변경 내용, 확인한 근거, 실행한 검증, 남은 문제를 간결하게 보고한다. 아직 실행하지 않은 테스트나 배포를 완료했다고 쓰지 않는다. 모의 응답을 실제 API 데이터라고 표현하지 않는다.

완료 여부는 아래 기준으로 판단한다.

- 필수 조건 누락 시 질문하고, 답변을 받아 같은 요청을 이어서 처리한다.
- 실제 API 데이터로 후보를 조회하고 근거·조회 범위·시각을 표시한다.
- 상태에 따라 여러 도구를 선택하고 서로 다른 그래프 경로가 실행된다.
- 검증 가능한 오류를 감지해 수정·재실행하고 반복 한도에서 종료한다.
- 단기 기억과 장기 기억이 분리되며 현재 요청 조건이 우선 적용된다.
- 요약 후에도 검색 조건과 근거가 보존된다.
- 저장 검색을 재사용하고 주기적 검색 없이 확정된 이벤트에서 문자 또는 Discord DM 알림을 발송한다. 자동 감지 이벤트가 없으면 그 한계와 데모 트리거를 명시한다.
- 같은 기준으로 성찰 적용 전후를 측정하고 결과를 기록한다.
- 배포된 화면에서 핵심 흐름을 체험할 수 있다.
- 미지원 기능·미확정 설정·외부 서비스 제약을 문서에 명시한다.

## 13. 추가 기능: 루트 페이지 검색 결과의 ANIMAL_API 연동

추가 요청일: 2026-11-10

### 요구사항과 구현 내용

- 루트 페이지(`/`)의 `구조동물 찾기`로 검색하면 백엔드 `POST /api/v1/searches`를 거쳐 국가동물보호정보시스템 ANIMAL_API의 실제 공고를 조회한다.
- 백엔드는 `ANIMAL_API_KEY`와 기존 `.env`에서 사용 중인 `ANIMAL_API_SERVICE_KEY`를 모두 지원한다. 두 이름이 모두 있으면 `ANIMAL_API_KEY`를 우선하며, 비밀 키는 서버에서만 사용한다.
- 동물 API 키가 설정되어 있으면 `APP_MODE=local`, `STORAGE_BACKEND=sqlite`에서도 실제 데이터를 조회한다. 실제 공고 검색만을 위해 OpenAI 호출이나 Supabase 전환을 강제하지 않는다. 키가 없고 로컬 모드인 경우에만 명시적인 샘플 데이터를 사용한다.
- 지역 목록은 `sido_v2`, 공고 검색은 `abandonmentPublic_v2`로 연결한다. 선택 지역은 공식 코드로 매핑하고 기간은 `YYYYMMDD`, 동물 종류는 공식 축종 코드로 전달한다. 전체 종류를 선택하면 축종 필터를 생략한다.
- 공식 기본 주소는 `https://apis.data.go.kr/1543061/abandonmentPublicService_v2`이다. 기존 `http://apis.data.go.kr/` 설정은 HTTPS로 보정하고 일반 키와 URL 인코딩 키를 지원한다.
- 공고 응답을 기존 후보 형식으로 정규화해 사진·품종·털색·특징·발견 일자·위치·보호센터·연락처를 표시한다. 기존 조건 검증·후보 정렬·페이지 상한·상위 10건 표시를 유지한다.
- 상태 API(`/api/v1/health`)와 검색 응답에 `animal_data_source`(`api` 또는 `sample`)를 추가한다. 루트 페이지의 배지·안내문 및 실행 이력이 실제 데이터 출처를 표시한다. `mode=local`과 샘플 사용 여부를 같은 의미로 취급하지 않는다.
- 지역 목록 요청이 실패해도 성공한 상태 확인 결과는 유지하고 API의 오류 안내를 보여 준다. 실제 조회의 인증 오류·통신 실패를 빈 검색 결과나 샘플 데이터로 대체하지 않는다.
- 로컬 실행에서는 실제 공고를 조회하더라도 알림을 발송하지 않으며 알림 신청 버튼의 서버 설정 상태도 이에 맞게 표시한다.

### 적용과 검증

- `.env`의 `ANIMAL_API_KEY` 또는 `ANIMAL_API_SERVICE_KEY`를 설정하고 백엔드를 재시작한 뒤 루트 페이지를 새로고침한다. 로컬 검색에는 `APP_MODE=local`, `STORAGE_BACKEND=sqlite`를 사용할 수 있다.
- 변경 파일: `backend/config.py`, `backend/tools.py`, `backend/main.py`, `backend/graph.py`, `frontend/src/main.jsx`, `tests/test_api.py`, `.env.example`, `README.md`, `docs/architecture.md`.
- `python -m pytest -q -p no:cacheprovider`: **29개 통과**. 모의 외부 응답을 사용하는 API 통합 테스트로 두 키 이름, 검색 조건 전달, 실제 후보 형식, 인증 실패 시 샘플 대체 금지를 검증했다.
- `frontend`에서 `npm run build`: **통과**.
- 최초 외부 조회는 HTTP 403, `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`, 사유 코드 `30`(등록되지 않은 서비스키)으로 실패했다. 후속 진단에서 `.env`의 `ANIMAL_API_SERVICE_KEY` 값 끝에 설명용 `_Decoding` 문자열이 포함되어 있음을 확인했다. 이 문자열까지 키로 전송한 것이 원인이며 활용 승인 문제로 단정할 수 없었다.
- `.env`에서 키 뒤의 `_Decoding`만 제거한 뒤 실제 API 조회에 성공했다. 서울·최근 14일·전체 종류 검색에서 첫 페이지 50건/전체 170건을 확인했고, 서울·강아지·최근 14일 조건의 실제 검색 워크플로에서는 2페이지/전체 71건을 조회하여 상위 후보 10건을 반환했다(`status=completed`, 오류 없음). 조회 시점에 따라 건수는 달라질 수 있다.
- `Encoding`/`Decoding`은 포털의 키 구분 설명이며 키 값에 접미사로 덧붙이지 않는다. 키 원문은 출력하거나 이 문서에 기록하지 않는다. 설정을 캐시한 실행 중 백엔드는 `.env` 변경 후 재시작한다.

## 14. 프론트엔드 Vercel 배포 설정

사용자 확정 사항: 프론트엔드는 `https://vibe-codeing-demo.vercel.app/`에 배포한다. 앞 절의 Render Static Site 추천보다 이 선택을 우선한다. 백엔드는 기존 `https://meet-again-ghbye-api.onrender.com`의 FastAPI 서비스를 계속 사용한다.

### Vercel 프로젝트 설정

저장소 루트에서 프로젝트를 가져온 경우 아래 설정을 사용한다.

| 항목 | 값 |
| --- | --- |
| Framework Preset | `Vite` |
| Root Directory | `frontend` |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

명령과 출력 경로는 `frontend`를 기준으로 한다. Root Directory를 `frontend`로 지정했다면 출력 경로를 `frontend/dist`로 중복 지정하지 않는다. 배포 브랜치에는 최신 프론트엔드 변경 사항이 포함되어야 한다.

### 프론트엔드 환경변수

Vercel 프로젝트의 Settings → Environment Variables에서 설정한다.

```dotenv
VITE_API_BASE_URL=https://meet-again-ghbye-api.onrender.com/api/v1
```

- 위 값은 사용자가 확정한 기존 Render 백엔드의 API 주소이다. 끝에 `/api/v1`을 한 번만 포함한다. `localhost`나 `127.0.0.1`을 배포용 값으로 사용하지 않는다.
- Production 환경에 설정한다. Preview 배포에서도 검색을 사용하려면 Preview에도 설정한다.
- 현재 코드의 기본값 `/api/v1`은 같은 도메인으로 요청한다. 로컬 `vite.config.js`의 `server.proxy`는 개발 서버 전용이므로 Vercel 정적 배포에서 백엔드 프록시를 제공하지 않는다. 현재 구성은 공개 백엔드 절대 주소를 사용한다.
- 환경변수를 변경한 뒤 반드시 새 빌드로 Redeploy한다. Vite의 `VITE_` 값은 빌드 시 번들에 반영되므로 기존 배포에는 자동 적용되지 않는다.
- `ANIMAL_API_KEY`, `ANIMAL_API_SERVICE_KEY`, `OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DISCORD_BOT_TOKEN`은 백엔드 서버에만 설정한다. 이 값에 `VITE_` 접두어를 붙이거나 루트 `.env` 전체를 프론트엔드 환경변수로 옮기지 않는다.

### 백엔드 연결 설정

백엔드 호스팅 서비스의 환경변수에 확정된 Vercel origin을 등록한다. 기존에 필요한 origin은 유지하면서 아래 Vercel 주소를 추가한다.

```dotenv
CORS_ORIGINS=http://localhost:5173,https://vibe-codeing-demo.vercel.app
ANIMAL_API_BASE_URL=https://apis.data.go.kr/1543061/abandonmentPublicService_v2
```

- `CORS_ORIGINS`에는 프로토콜과 호스트만 넣는다. 경로(`/api/v1` 등)와 마지막 `/`는 넣지 않는다. 커스텀 도메인이 있으면 쉼표로 추가한다.
- 현재 CORS 구현은 정확한 origin 목록을 사용한다. Preview 주소는 Production 주소와 다르므로 필요한 Preview origin도 별도로 추가한다. `https://*.vercel.app` 같은 패턴은 현재 코드에서 지원하지 않는다.
- 백엔드에 실제 동물 API 키를 `ANIMAL_API_KEY` 또는 `ANIMAL_API_SERVICE_KEY` 중 하나로 설정한다. `_Decoding`/`_Encoding` 설명 문자열을 키에 덧붙이지 않는다.
- 로컬 `.env`는 Git에서 제외되어 있다. 로컬 키 수정은 배포 서버에 자동 반영되지 않으므로 호스팅 서비스의 환경변수도 수정해야 한다.
- 로컬에서 수정한 최신 백엔드 코드도 배포한다. 이전 배포가 `APP_MODE=local`에서 무조건 샘플을 반환하는 버전이면 환경변수만 설정해도 새 동작이 적용되지 않는다.
- 실제 공고 조회만 필요하면 최신 코드에서 `APP_MODE=local`, `STORAGE_BACKEND=sqlite`와 동물 API 키 조합을 사용할 수 있다. OpenAI·Supabase·알림까지 사용하는 기존 `APP_MODE=live`의 필수 조건은 유지한다. 배포 서버에서 SQLite를 쓰는 경우 저장 검색·실행 이력은 호스팅 저장소의 영속성에 따르며, Vercel 프론트엔드 배포만으로 영속성이 보장되지 않는다.
- 환경변수 변경 후 백엔드를 재시작하거나 재배포한다.

### 지도와 라우팅

- 지도를 표시할 경우 Vercel에 `VITE_KAKAO_JS_KEY`를 추가하고 카카오 앱의 웹 도메인 설정에 실제 Vercel/커스텀 도메인을 등록한다. 보호센터 주소를 좌표로 변환하는 `KAKAO_REST_API_KEY`는 백엔드에 설정한다. 지도 키가 없어도 공고 검색과 주소 표시는 가능하다.
- 현재 화면은 `/`에서 상태로 탭을 전환하므로 SPA fallback용 `vercel.json`은 필수가 아니다. 향후 `/saved`, `/history` 같은 클라이언트 경로를 추가하면 새로고침을 위한 SPA rewrite를 설정한다.

### 배포 후 확인과 남은 정보

1. 백엔드 `/api/v1/health`에서 `animal_data_source=api`를 확인한다. 해당 필드가 없으면 배포 코드 버전도 확인한다. `mode=local`이어도 실제 데이터 조회는 가능하다.
2. Vercel 화면의 브라우저 Network에서 `/health`, `/regions` 요청이 지정한 백엔드 HTTPS 주소로 전송되고 JSON을 반환하는지 확인한다.
3. 검색 시 세션 생성(`/sessions`)과 `/searches`가 정상 처리되고 실제 후보·조회 시각·범위가 표시되는지 확인한다. GET뿐 아니라 Authorization·Content-Type 헤더가 포함되는 요청의 CORS 사전 요청도 확인한다.
4. 환경변수 누락으로 Vercel 자체 `/api/v1/...`에 요청하거나 HTML/404가 반환되면 `VITE_API_BASE_URL`과 재배포 여부를 확인한다. CORS 오류면 백엔드 허용 origin을 확인한다.
5. Production URL은 `https://vibe-codeing-demo.vercel.app/`, 백엔드 URL은 `https://meet-again-ghbye-api.onrender.com`으로 사용자 확인을 받았다. 추가 커스텀/Preview URL과 프론트엔드·백엔드 배포 브랜치/커밋은 확인 후 배포 기록에 남긴다. Vercel/Render 대시보드 설정을 변경했다는 의미는 아니다.

### 확정 주소의 실제 점검 결과와 필요한 조치 (2026-11-10)

- Vercel 루트 페이지는 HTTP 200이다. 공개 JS `/assets/index-CErlEpbP.js`에서 API 기본 주소가 상대 경로 `/api/v1`로 빌드된 것을 확인했다. 따라서 현재 배포는 Vercel 도메인으로 API를 요청하며, 실제 `https://vibe-codeing-demo.vercel.app/api/v1/health`는 HTTP 404를 반환했다.
- Vercel의 Production 환경변수에 `VITE_API_BASE_URL=https://meet-again-ghbye-api.onrender.com/api/v1`을 설정하고 최신 프론트엔드 코드로 다시 빌드·배포한다. 현재 공개 JS에는 최신 `animal_data_source` UI도 포함되어 있지 않다.
- Render 백엔드 `/api/v1/health`는 재확인에서 HTTP 200을 반환했다. 응답은 `mode=local`, `storage=sqlite`이며 최신 코드에 추가한 `animal_data_source` 필드는 없었다. 최신 백엔드 수정이 배포되지 않은 상태로 판단되므로 최신 코드를 배포하고, 서버 환경변수에 수정된 동물 API 키를 설정한다. 키 값은 이 문서에 기록하지 않는다.
- `Origin: https://vibe-codeing-demo.vercel.app`으로 백엔드를 호출했을 때 `Access-Control-Allow-Origin` 헤더가 없었다. `/api/v1/searches`에 대한 POST 사전 요청은 HTTP 400과 `Disallowed CORS origin`을 반환했다. Render의 기존 `CORS_ORIGINS` 목록에 `https://vibe-codeing-demo.vercel.app`을 추가하고 변경한 설정이 반영되는 새 배포를 실행한다. 기존에 필요한 origin은 유지한다.
- 최종 순서: 백엔드에 최신 코드·동물 API 키·CORS 설정 반영 → 백엔드 health의 `animal_data_source=api` 및 Vercel origin의 사전 요청 성공 확인 → Vercel에 API 주소 설정 후 최신 프론트엔드 Redeploy → 배포 화면에서 검색 확인.
- 위 점검은 공개 페이지·JS·GET·OPTIONS 응답에 대한 읽기 전용 검사다. Vercel/Render 환경변수 변경이나 실제 재배포, 배포 화면에서의 검색 완료는 아직 수행하지 않았다.

공식 참고: [Vercel 빌드 설정](https://vercel.com/docs/builds/configure-a-build), [Vercel 환경변수와 재배포](https://vercel.com/docs/environment-variables), [Vite 환경변수](https://vite.dev/guide/env-and-mode), [Vite 개발 서버 옵션](https://vite.dev/config/server-options.html), [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), [카카오맵](https://developers.kakao.com/docs/ko/kakaomap/common).

## 15. Render 백엔드 환경변수 전체 목록

대상 서비스는 `meet-again-ghbye-api`이다. Render Dashboard → 해당 서비스 → Environment에서 설정한다. 아래 기본 구성은 실제 동물 공고 조회와 규칙 기반 계획을 사용한다. `ANIMAL_API_KEY`의 예시 문구는 실제 키로 교체하며 키 원문은 문서에 저장하지 않는다.

```dotenv
APP_MODE=local
STORAGE_BACKEND=sqlite
SQLITE_PATH=.data/meet-again.db
ANIMAL_API_KEY=발급받은_실제_키로_교체
ANIMAL_API_BASE_URL=https://apis.data.go.kr/1543061/abandonmentPublicService_v2
CORS_ORIGINS=http://localhost:5173,https://vibe-codeing-demo.vercel.app,https://meet-again-ghbye-demo.onrender.com
MAX_SEARCH_PAGES=3
MAX_REFLECTIONS=2
MAX_TOOL_CALLS=30
REQUEST_TIMEOUT_SECONDS=60
```

- `APP_MODE=local`이어도 최신 코드에서 동물 API 키가 있으면 실제 공고를 조회한다. 이 구성에서는 OpenAI를 호출하거나 Discord 알림을 발송하지 않는다.
- `ANIMAL_API_SERVICE_KEY`는 `ANIMAL_API_KEY` 대신 사용할 수 있는 별칭이다. 하나만 설정하며, 둘 다 설정하면 `ANIMAL_API_KEY`가 우선한다. `_Decoding`/`_Encoding` 설명 문자열은 붙이지 않는다.
- `CORS_ORIGINS` 예시는 로컬 개발·현재 Vercel·기존 Render 화면을 허용한다. 실제로 계속 사용할 기존 origin은 유지하고 필요한 Preview/커스텀 도메인을 추가한다.
- `SQLITE_PATH`는 서버 파일 경로이며 일반 배포 파일시스템의 영속성을 보장하지 않는다. 저장 기록을 계속 유지해야 한다면 별도로 준비된 Supabase 저장소를 사용한다.
- 숫자 설정의 허용 범위: `MAX_SEARCH_PAGES` 1~10, `MAX_REFLECTIONS` 0~3, `MAX_TOOL_CALLS` 10~60, `REQUEST_TIMEOUT_SECONDS` 10~120초. 위 값은 코드의 기본값이므로 동일하게 사용할 경우 생략할 수 있다.

나머지 애플리케이션 환경변수는 다음과 같다. 사용하지 않는 기능의 키는 등록하지 않아도 된다.

| 이름 | 값 또는 설정 방법 | 필요한 경우 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 본인의 OpenAI API 키 | `APP_MODE=live` 필수 |
| `OPENAI_MODEL` | `gpt-6-luna` | OpenAI 계획 생성. 해당 모델의 실제 계정 접근 권한 별도 확인 |
| `SUPABASE_URL` | `https://yaywavgjaquftvekuvsb.supabase.co` | `STORAGE_BACKEND=supabase` |
| `SUPABASE_SCHEMA` | `aio-03-p2-team1-demo` | `STORAGE_BACKEND=supabase` |
| `SUPABASE_SERVICE_ROLE_KEY` | 해당 Supabase 프로젝트의 서버 전용 service role 키 | `STORAGE_BACKEND=supabase` 필수 |
| `KAKAO_REST_API_KEY` | 카카오 REST API 키 | 보호센터 주소의 좌표 변환 |
| `DISCORD_BOT_TOKEN` | Discord Bot 토큰 | Discord DM 알림 |
| `DISCORD_ALLOWED_USER_IDS` | 동의받은 수신자 ID, 여러 명은 쉼표 구분 | Discord DM 알림 |

전체 실제 연동을 사용하려면 기본 구성에서 `APP_MODE=live`, `STORAGE_BACKEND=supabase`로 변경하고 OpenAI·Supabase 필수 키를 설정한다. 지정 스키마의 `documents` 테이블과 Data API 접근 설정도 준비되어 있어야 한다. `STORAGE_BACKEND=supabase`는 `APP_MODE=local`과도 조합할 수 있으며, 이 경우 OpenAI 키는 필수가 아니다. Discord 알림에는 전체 실제 연동 구성 외에 Bot 토큰·허용 목록·사용자의 알림 신청과 동의가 필요하다.

`animal_data_source`는 코드가 계산해 반환하는 응답 필드이므로 Render 환경변수로 등록하지 않는다. `VITE_API_BASE_URL`과 `VITE_KAKAO_JS_KEY`는 Vercel 프론트엔드 설정이다. `PORT`는 Render 기본값을 사용하고 시작 명령에서 `$PORT`를 읽는다.

환경변수를 저장만 해 두면 실행 중인 서비스에는 적용되지 않는다. 최신 코드 배포와 함께 설정을 반영하고 `/api/v1/health` 및 실제 검색을 확인한다. Render의 `Save, rebuild, and deploy`는 새 빌드·배포, `Save and deploy`는 기존 빌드에 새 설정으로 배포, `Save only`는 다음 배포까지 적용을 보류한다. 새 코드가 Git 배포 브랜치에 반영되어 있는지도 별도로 확인한다.

참고: [Render 환경변수 설정](https://render.com/docs/configure-environment-variables), [Render 기본 환경변수](https://render.com/docs/environment-variables).

## 16. OpenAI·Supabase 전체 연동으로 전환

사용자 요청에 따라 로컬 `.env`의 `APP_MODE=live`, `STORAGE_BACKEND=supabase`를 변경했다. 샘플 체험용 코드 기본값과 `.env.example`의 기본 모드는 유지한다. 사용자가 선택한 Render 작업 공간은 `G.H. Byeon's Workspace`(`tea-cspstp8gph6c73es77r0`)이며 변경 대상은 `meet-again-ghbye-api`(`srv-dbnk8hqjnfac73ckg0mg`)이다.

### Render와 로컬에 필요한 값

```dotenv
APP_MODE=live
STORAGE_BACKEND=supabase
SUPABASE_URL=https://yaywavgjaquftvekuvsb.supabase.co
SUPABASE_SCHEMA=aio-03-p2-team1-demo
OPENAI_MODEL=gpt-6-luna
```

`OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, 동물 API 키(`ANIMAL_API_KEY` 또는 `ANIMAL_API_SERVICE_KEY`)도 서버에 설정한다. 비밀 키 원문은 이 문서에 기록하지 않는다. 기존 `CORS_ORIGINS`에는 `https://vibe-codeing-demo.vercel.app`을 포함한다. `live` 전환 시 동의·신청·수신자 허용 조건을 갖춘 Discord 알림도 기존 코드에 따라 활성화될 수 있다.

로컬 연결 검사 결과:

- Pydantic 설정 검증은 통과했고 두 모드 값과 `animal_data_source=api`를 확인했다.
- 현재 로컬 `OPENAI_API_KEY`로 계획 생성 요청을 보냈을 때 **HTTP 401 / `invalid_api_key`** 가 반환됐다. 유효한 OpenAI 프로젝트 API 키를 로컬 `.env`와 Render에 각각 설정해야 한다. 모델은 자동 변경하지 않았다. Render에 별도로 설정된 키의 유효성까지 검사한 결과는 아니다.
- Supabase Data API에서 `Accept-Profile: aio-03-p2-team1-demo`로 `documents`를 읽으려 했을 때 **HTTP 406 / `PGRST106` / `Invalid schema`** 가 반환됐다. 현재 API에서 이 스키마로 접근할 수 없다는 의미이며, 아래 Exposed schemas 설정과 스키마 존재 여부를 확인한다.
- Supabase 관리 연결 도구는 권한 오류로 테이블 목록을 반환하지 않았다. 원격 테이블 존재·구조를 확인하지 못했으므로 원격 DDL은 실행하지 않았다.

Render 변경과 배포 검증 결과:

- 사용자가 작업 공간을 선택한 뒤 `meet-again-ghbye-api`의 `APP_MODE=live`, `STORAGE_BACKEND=supabase`를 병합 방식으로 저장했다. 다른 환경변수는 교체하지 않았다.
- Render 도구는 환경변수 수정과 함께 자동으로 새 배포 `dep-dbpelc6gekts739ocu8g`를 시작했다. 연결 브랜치는 `codex/meet-again-demo`, 배포 커밋은 `4b7bfaaddb70521c4d3937749d9908890a830254`이다. 로컬 미커밋 수정 사항을 푸시한 것은 아니다.
- 배포의 최종 상태는 **`update_failed`** 이다. 시작 로그의 직접 원인은 `실제 연동 모드 설정 누락: openai_api_key, animal_api_key`이며, Render에 `OPENAI_API_KEY`와 `ANIMAL_API_KEY`가 필요하다. 구버전 배포에서는 동물 키 별칭 지원도 기대하지 말고 `ANIMAL_API_KEY`를 사용한다.
- 실패 후 공개 health는 HTTP 200, `mode=local`, `storage=sqlite`, `animal_data_source` 없음으로 응답했다. 설정값 저장은 완료했으나 실행 중인 서비스의 live 전환은 완료되지 않았다.
- 후속 작업은 유효한 OpenAI 키·동물 API 키·Supabase 서버 키를 Render에 설정하고, Supabase 테이블/스키마 접근을 준비한 뒤 최신 코드를 배포하는 것이다. 로컬의 OpenAI 키는 검증에 실패했으므로 그대로 서버에 복사하지 않는다. Supabase 키의 Render 등록 상태는 이번 시작 실패 로그만으로 확정하지 않았다.
- 사용자 재실행 후 배포 `dep-dbpesj88v5cc73e2j4ag`도 동일한 커밋 `4b7bfaaddb70521c4d3937749d9908890a830254`에서 `update_failed`로 끝났다. `openai_api_key, animal_api_key` 누락 메시지는 외부 API가 키를 거절한 단계가 아니라 서버 설정 검사에서 두 값이 비어 있다는 뜻이다. 로컬 `.env`의 값은 Render로 자동 전달되지 않는다. `meet-again-ghbye-api`의 Environment에 `OPENAI_API_KEY`, `ANIMAL_API_KEY`라는 정확한 이름과 비어 있지 않은 실제 값을 등록한다. 현재 구버전에는 `ANIMAL_API_SERVICE_KEY` 별칭 지원이 없으므로 `ANIMAL_API_KEY`를 사용한다. 저장 후 새 환경변수가 반영되는 배포를 수행한다.

### Supabase 테이블과 스키마 설정 절차

1. 프로젝트 `yaywavgjaquftvekuvsb`의 SQL Editor에서 기존 스키마와 `documents` 테이블이 있는지 확인한다. Table Editor의 스키마 선택으로도 확인할 수 있다. 같은 이름의 테이블이 이미 있다면 아래 구조와 호환되는지 먼저 확인한다.
2. 테이블이 없다면 저장소의 `scripts/bootstrap_schema.sql` 내용을 SQL Editor에서 검토·실행한다. 이 파일은 `"aio-03-p2-team1-demo".documents` 생성, 복합 기본키·인덱스, RLS 활성화, 서버 역할 권한을 설정한다. 정식 마이그레이션 이력 파일은 아니며 기존 테이블 구조를 자동 변경하지 않는다.
3. [Data API 설정](https://supabase.com/dashboard/project/yaywavgjaquftvekuvsb/integrations/data_api/settings)에서 Data API를 활성화하고 **Exposed schemas**에 `aio-03-p2-team1-demo`를 추가한 뒤 저장한다. 기존에 사용하는 노출 스키마는 유지한다. SQL의 스키마명에는 하이픈 때문에 큰따옴표가 필요하지만 대시보드 입력에는 이름만 넣는다.
4. [API Keys](https://supabase.com/dashboard/project/yaywavgjaquftvekuvsb/settings/api)에서 현재 Python 어댑터와 호환되는 legacy `service_role` JWT를 확인해 Render의 `SUPABASE_SERVICE_ROLE_KEY`에 설정한다. 현재 어댑터는 이 값을 `apikey`와 Bearer 헤더 양쪽에 사용한다. `anon`/publishable 키는 이 서버 전용 저장소에 사용하지 않는다. 새 `sb_secret_...` 키를 도입하려면 헤더 처리 호환성을 별도 확인한다.
5. 앱은 브라우저에서 Supabase를 직접 호출하지 않고 FastAPI를 거쳐 접근한다. `documents`에는 RLS를 활성화하고 `service_role`에 스키마 USAGE와 SELECT·INSERT·UPDATE·DELETE를 허용한다. `anon`/`authenticated`용 공개 접근 권한·전체 허용 정책을 추가하지 않는다. 소유자 격리는 백엔드의 해시된 데모 세션 토큰과 owner 필터가 담당한다.

필요한 테이블 구조:

| 열 | 형식 | 조건 |
| --- | --- | --- |
| `owner` | text | NOT NULL, 세션 소유자 해시 |
| `kind` | text | NOT NULL, identity/thread/memory/saved/run/subscription/notification |
| `id` | text | NOT NULL |
| `data` | jsonb | NOT NULL |
| `updated_at` | timestamptz | NOT NULL, 기본값 now() |

기본키는 `(owner, kind, id)`이며 `(owner, kind, updated_at desc)` 인덱스를 사용한다. 저장 데이터가 기존 SQLite에 있다면 이 설정 변경만으로 Supabase로 이관되지는 않는다.

### Vercel API 주소 설정

Vercel의 해당 프로젝트 → Settings → Environment Variables에 다음 항목을 등록한다.

```dotenv
VITE_API_BASE_URL=https://meet-again-ghbye-api.onrender.com/api/v1
```

Environment는 Production을 선택하며 Preview에서도 검색할 경우 Preview에도 적용한다. 저장 후 최신 프론트엔드 코드로 Redeploy한다. `/api/v1`을 중복으로 덧붙이지 않는다. Supabase 서버 키·OpenAI 키·동물 API 키는 Vercel 프론트엔드 변수에 넣지 않는다.

### 전환 완료 검증

`/api/v1/health`의 `mode=live`, `storage=supabase`, 최신 코드의 `animal_data_source=api`를 확인한다. health는 설정 상태만 반환하므로 OpenAI·Supabase 연결 성공을 보장하지 않는다. 실제 검색에서 OpenAI 계획 생성·공고 조회가 성공하고, 검색 저장 후 다시 불러와 Supabase 쓰기·읽기를 확인해야 전환 완료로 판단한다.

공식 참고: [Supabase 사용자 지정 스키마](https://supabase.com/docs/guides/api/using-custom-schemas), [Supabase API 권한과 RLS](https://supabase.com/docs/guides/api/securing-your-api), [OpenAI API 인증](https://developers.openai.com/api/reference/overview), [Vercel 환경변수](https://vercel.com/docs/environment-variables).

## 17. OpenAI 계획 생성 오류의 원인 구분 (2026-11-11)

사용자에게 표시된 `OpenAI 계획 생성 실패: 모델 접근 권한·API 키·응답을 확인하세요.`는 기존 코드가 여러 예외를 같은 문장으로 처리한 결과다. 이 메시지만으로 인증키 오류·모델 권한·사용 한도 중 원인을 단정하지 않는다.

확인 결과:

- Render 배포 `dep-dbpf1ijm8hqs73dnti7g`는 live이며 공개 health에서 `mode=live`, `storage=supabase`, `model=gpt-6-luna`를 확인했다. 이전 환경변수 누락으로 서버 시작이 실패한 상황과 구분한다.
- 배포 커밋은 여전히 `4b7bfaaddb70521c4d3937749d9908890a830254`이고 공개 health에 `animal_data_source`는 없었다.
- 로컬 `.env`의 OpenAI 키로 동일한 계획 요청을 한 번 실행했을 때 HTTP 401 / `invalid_api_key`가 반환됐다. 로컬 키는 교체가 필요하다. Render에 설정된 키가 로컬과 같다고 확인한 것은 아니며, Render 로그에서도 실제 OpenAI 오류 코드가 확인되지 않았다.

`backend/tools.py`의 Planner를 수정해 아래 오류를 구분한다.

| 오류 코드 | 의미와 조치 |
| --- | --- |
| `llm_auth` | HTTP 401. 백엔드 `OPENAI_API_KEY`를 유효한 키로 교체하고 새 배포에 반영 |
| `llm_permission` | HTTP 403. 프로젝트·키의 모델 및 요청 권한 확인 |
| `llm_model` | HTTP 404. `OPENAI_MODEL` 이름과 해당 프로젝트의 모델/리소스 접근 확인 |
| `llm_quota` | HTTP 429와 확인된 크레딧·지출·사용 한도 코드. 결제와 한도를 확인 |
| `llm_rate_limit` | 그 외 HTTP 429. 오류 코드·호출 한도를 확인하고 제한된 재시도 |
| `llm_timeout` / `llm_network` | 응답 시간 초과 / 통신 실패 |
| `llm_request` / `llm_upstream` | 요청 설정 오류 / OpenAI 서버 오류 |
| `llm_response` | 미완료 응답·JSON 오류·잘못된 도구 목록 또는 근거 형식 |

화면과 실행 결과에는 분류된 오류와 조치만 전달한다. 서버 로그에는 HTTP 상태·허용된 오류 코드·형식을 확인한 request ID만 기록하며, 원본 SDK 예외 메시지·응답 본문·인증키는 출력하지 않는다. 모델을 임의로 변경하거나 샘플 데이터로 우회하지 않는다.

검증: HTTP 오류·네트워크 오류·응답 형식·키 비노출을 포함해 백엔드 테스트 **44개 통과**. 이번 코드 수정은 로컬에 있으며 Render에 배포하지 않았다. Render 원인을 구분하려면 최신 코드를 배포한 뒤 새 검색의 구체적인 오류 또는 정제된 로그를 확인한다.

참고: [OpenAI 공식 오류 코드 안내](https://developers.openai.com/api/docs/guides/error-codes).

## 18. Redis 기반 사용자 로그인 추가 (2026-11-11)

사용자의 새 요청에 따라 기존 로그인 생략·익명 데모 인증 요구를 회원가입/로그인 기능으로 대체한다.

구현한 화면과 기능:

- 루트 페이지 오른쪽 위에 로그인 버튼을 추가하고 `/login`으로 이동시킨다. 로그인 후 사용자 이름과 로그아웃 버튼을 표시한다.
- `/login`에 이메일·비밀번호 로그인과 이름·이메일·비밀번호 회원가입 폼을 제공한다. 비밀번호 표시 전환, 입력 검증, 처리 중 상태, 오류 안내, 홈으로 돌아가기를 지원한다.
- 로그인 성공 시 루트로 이동하고 새로고침 시 `/auth/me`로 로그인 상태를 복원한다. 인증 만료 시 로그인 화면으로 이동한다. 로그아웃/계정 전환 시 이전 계정 화면 상태를 초기화한다.
- 검색·저장 검색·기억·실행 이력·알림은 로그인 사용자 UUID를 기준으로 격리한다. 익명 `POST /api/v1/sessions`와 기존 Bearer 데모 토큰은 인증에 사용하지 않는다.

백엔드 구성:

- 신규 `backend/auth.py`: Argon2 비밀번호 해시, 회원가입·로그인·현재 사용자·로그아웃 API.
- 계정은 기존 SQLite 또는 Supabase `documents`의 `identity/account` 문서에 저장한다. 정규화한 이메일의 SHA-256으로 계정 문서 소유자 키를 만들고 create-only 저장으로 중복 가입을 막는다. 기존 스키마의 `identity` 종류를 재사용하므로 DB DDL 변경은 필요 없다.
- Redis에는 세션과 로그인 호출 제한만 저장한다. 세션 원문은 임의의 32바이트 토큰이며 Redis 키에는 SHA-256만 사용한다. 기본 TTL은 24시간이고 로그인 시 현재 브라우저의 기존 세션을 회전하며 로그아웃 시 폐기한다.
- 브라우저 인증은 HttpOnly 쿠키(`meet_again_session`, Path=/api/v1)로 처리한다. 토큰을 응답 JSON이나 localStorage에 저장하지 않는다. API는 no-store 응답과 credentialed CORS를 적용하고 변경 요청의 Origin을 검사한다.
- Redis 연결 실패 시 503으로 응답하고 인증을 우회하지 않는다. 잘못된 로그인은 이메일 존재 여부와 관계없이 같은 메시지를 표시한다. 잘못된 입력의 422 응답에도 비밀번호 등 원본 입력값을 포함하지 않는다.

새 환경변수:

```dotenv
# Render: 로그인 전용 Key Value의 Internal URL. 실제 URL은 서버에만 설정한다.
REDIS_URL=redis://로그인용_redis_호스트:6379/0
AUTH_SESSION_TTL_SECONDS=86400
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
```

로컬에는 저장소 루트에서 `docker compose up -d redis`로 전용 Redis를 실행하고 `REDIS_URL=redis://127.0.0.1:6380/0`을 사용한다. HTTP 개발 환경에서는 `AUTH_COOKIE_SECURE=false`로 지정한다. Secure 기본값은 APP_MODE가 live이면 true, local이면 false다. Redis 7 이상 또는 호환 Valkey가 필요하다. 자격 증명이 포함된 Redis URL은 프론트엔드나 저장소에 기록하지 않는다.

Vercel 배포 설정 변경:

```dotenv
VITE_API_BASE_URL=/api/v1
```

기존 절의 Render 절대 API 주소 설정은 이번 쿠키 인증 구성에서는 위 상대 경로로 변경한다. `frontend/vercel.json`의 `/api/v1/:path*` rewrite가 기존 Render API를 프록시해 같은 사이트의 쿠키로 인증하고 `/login` 새로고침은 index.html로 처리한다. 백엔드의 허용 origin에는 `https://vibe-codeing-demo.vercel.app`을 유지한다. 프론트엔드·백엔드 모두 최신 코드를 배포해야 한다.

Render 연결 조회에서는 다른 프로젝트의 `house-tour-notes-kv`만 확인되어 재사용하거나 변경하지 않았다. 로그인 전용 Key Value 생성·REDIS_URL 등록·원격 서비스 배포는 이번 코드 작업에서 수행하지 않았다. 기존 SQLite 익명 기록은 회원 계정으로 자동 이관하지 않는다. 이메일 인증·비밀번호 재설정·계정 삭제·모든 기기 로그아웃은 후속 범위다.

검증 결과:

- 백엔드 테스트 **53개 통과**. Redis 호환 모의 서버를 사용해 쿠키·비밀번호 해시·만료·회전·로그아웃·중복 가입·사용자 격리·호출 제한·CSRF·Redis 장애·비밀번호 비노출과 기존 검색을 검증했다.
- 프론트엔드 프로덕션 빌드 통과.
- 별도 로컬 Vite/API와 테스트 DB에서 HTTP로 루트·로그인 경로 200, 회원가입 201, 로그인 사용자·개인 이력 200, 로그아웃 204, 로그아웃 후 401을 확인했다. 테스트 API는 운영과 구분된 모의 Redis를 주입했다.
- 브라우저 직접 시각 검증은 자동화 앱 접근 승인 시간 초과로 완료하지 못했다. 실제 Redis/Render/Vercel 환경의 배포 후 로그인 검증은 아직 수행하지 않았다.

참고: [Redis asyncio 연결](https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html), [FastAPI 비밀번호 해싱](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [Vercel rewrites](https://vercel.com/docs/rewrites).

## 19. 로컬 회원가입 403 수정 (2026-11-11)

- 사용자가 접속한 주소는 `http://127.0.0.1:5173/login`이다. 로컬 `.env`의 `CORS_ORIGINS`에는 `http://localhost:5173`만 있어 회원가입 POST가 Origin 검사에서 403으로 차단되는 것을 재현했다.
- 로컬 `.env`의 기존 origin을 유지하면서 `http://127.0.0.1:5173`을 추가했다. `.env.example`에도 두 로컬 주소를 포함했다. 와일드카드나 임의 포트 허용으로 보안 검사를 우회하지 않는다.
- 로컬 `.env`가 `APP_MODE=live`여서 기본 쿠키가 Secure=true였다. HTTP 로컬 개발에서 로그인 쿠키를 사용할 수 있도록 이 로컬 파일에만 `AUTH_COOKIE_SECURE=false`를 설정했다. Render 운영에서는 계속 true를 사용한다.
- 차단 응답에 `code=origin_not_allowed`와 `CORS_ORIGINS` 확인 안내를 추가했다.
- 변경 전 같은 Origin의 빈 회원가입 요청은 403이었다. 변경 후 사전 요청은 200, 빈 POST는 422(입력 검증에 도달), 임의 외부 Origin은 계속 403임을 확인했다. 실행 중인 로컬 `127.0.0.1:8000` 서버에서도 동일한 빈 요청이 422이며 올바른 CORS 응답을 반환했다. 실제 계정은 이 진단에서 생성하지 않았다.
- 백엔드 회귀 테스트 **54개 통과**.

## 20. 로컬 회원가입 503과 Redis 실행 설정 (2026-11-11)

- 화면의 `로그인 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.`와 회원가입 503은 인증 처리 중 Redis 연결 실패로 발생했다. 로컬 Docker Desktop이 실행되지 않았고, `.env`는 `127.0.0.1:6379`를 가리키고 있었다.
- Docker Desktop 실행 후 기존 다른 프로젝트의 Valkey가 6379 포트를 사용하고 있음을 확인했다. 이 프로젝트에는 별도 컨테이너 `meet-again-redis`와 호스트 포트 6380을 구성했다.
- 루트 `compose.yaml`에 Redis 8, 로컬 인터페이스에만 공개하는 포트 `127.0.0.1:6380:6379`, AOF 영속화와 전용 볼륨, 상태 확인, 재시작 정책을 추가했다. `restart: unless-stopped`는 Docker 엔진이 실행된 상태에서 적용된다.
- 로컬 `.env`, `.env.example`, 백엔드 기본값의 `REDIS_URL`을 `redis://127.0.0.1:6380/0`으로 맞췄다. APP_MODE=live와 STORAGE_BACKEND=supabase는 유지했다. README에 실행·상태 확인 방법을 추가했다.

```powershell
docker compose up -d redis
docker compose ps
docker compose exec redis redis-cli ping
```

- 컨테이너 상태 `healthy`, Redis `PONG`, 앱 설정으로 연결한 Redis PING 및 호출 제한 트랜잭션 성공을 확인했다.
- 실행 중인 로컬 `http://127.0.0.1:8000` API에 존재하지 않는 임의 이메일로 로그인했을 때 503 대신 정상적인 인증 실패 401이 반환됐다. 이는 Redis 호출과 계정 저장소 조회가 처리되었음을 확인하는 진단이며 실제 사용자 계정을 생성하지 않았다.
- 실제 Redis의 별도 논리 DB와 임시 SQLite 계정 DB를 사용한 통합 확인에서 회원가입 201, 현재 사용자 조회 200, 로그아웃 204, 로그아웃 후 조회 401을 확인했다. 진단용 세션·호출 제한 키와 임시 계정 DB를 정리했다. 실제 Supabase 계정 생성은 이 검증에 포함하지 않았다.
- 이번 수정은 로컬 실행 환경에 적용했다. Render의 REDIS_URL은 별도 운영 Key Value 연결 URL을 사용해야 하며, 로컬 6380 주소를 Render에 입력하지 않는다.

## 21. Vercel 배포에서 백엔드 연결 실패 진단 (2026-11-11)

사용자 접속 주소: `https://vibe-codeing-demo-d6da1ptxi-aio-03-p2-team1.vercel.app/`. 화면 메시지는 `서버에 연결하지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.`다. 이 일반적인 화면 메시지만으로 서버 중단이라고 단정하지 않는다.

직접 확인한 원격 상태:

- Render `https://meet-again-ghbye-api.onrender.com/api/v1/health`는 HTTP 200이며 mode=live, storage=supabase다. 서버 자체는 응답한다.
- 위 Vercel 주소를 Origin으로 한 Render 사전 요청은 HTTP 400 / `Disallowed CORS origin`이다. 기존 운영 주소 `https://vibe-codeing-demo.vercel.app`의 사전 요청은 200이다. 새 주소에서 Render를 직접 호출하면 브라우저가 응답 접근을 차단한다.
- 새 Vercel 주소의 루트와 `/api/v1/health`는 외부 비로그인 요청을 Vercel SSO로 302 리다이렉트한다. 보호된 배포의 실제 앱 번들과 요청 주소는 확인하지 못했다. 배포 보호를 해제할 필요가 있다고 단정하지 않으며 실제 브라우저의 Network로 경로를 확인한다.
- 기존 운영 Vercel 주소에서는 `/api/v1/health`가 HTTP 404다. 공개 앱 번들은 `/api/v1`을 사용하고 있으나 현재 운영 배포에 API 프록시가 적용되지 않은 상태다. 새 보호된 배포에도 같은 상태라고 단정하지 않는다.
- Render `/api/v1/auth/me`는 HTTP 404다. 현재 live 배포는 `dep-dbprbgt9fdbs73f7q1lg`, 커밋 `4b7bfaaddb70521c4d3937749d9908890a830254`, 연결 브랜치는 `codex/meet-again-demo`다. 로컬 로그인 구현과 ANIMAL_API 데이터 출처 필드가 아직 배포되지 않았다.
- 로컬 Git에서 `frontend/vercel.json`, `backend/auth.py` 등은 아직 추적되지 않는 새 파일이다. 파일을 로컬에 생성하는 것만으로 Git 기반 배포에 반영되지 않는다.

최신 구현을 배포할 때 적용할 구성:

1. Vercel 프로젝트 Root Directory를 `frontend`로 설정하고 `frontend/vercel.json`이 배포 소스에 포함되게 한다. 이 파일의 `/api/v1/:path*` rewrite가 Render API로 전달하고 `/login`은 index.html로 전달한다.
2. Vercel에서 실제 배포 대상 환경(Production 및 Preview를 사용하는 경우 Preview)에 `VITE_API_BASE_URL=/api/v1`을 설정하고 새로 빌드·배포한다. 환경변수만 저장하거나 로컬 `.env`만 수정한 상태로 완료 처리하지 않는다.
3. Render의 기존 `CORS_ORIGINS` 목록을 보존하면서 사용 중인 Vercel 주소를 추가한다. 쿠키 인증에서도 변경 요청의 Origin 검사가 있으므로 같은 도메인 프록시를 사용해도 실제 프론트엔드 Origin은 허용되어 있어야 한다. 임의의 `*.vercel.app` 전체를 허용하지 않는다.

```dotenv
# 아래 두 주소를 기존 허용 목록에 추가 또는 병합한다.
CORS_ORIGINS=https://vibe-codeing-demo.vercel.app,https://vibe-codeing-demo-d6da1ptxi-aio-03-p2-team1.vercel.app
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
# REDIS_URL에는 운영용 Redis/Render Key Value 연결 URL을 설정한다.
```

4. 운영용 Redis를 연결한 뒤 인증 구현·의존성·잠금 파일을 포함한 최신 백엔드 코드를 Render 연결 브랜치에 반영하여 배포한다. 로컬 `127.0.0.1:6380`은 Render에서 사용할 수 없다. 기존 OpenAI·동물 API·Supabase 설정은 보존한다.
5. 완료 검증: Vercel `/api/v1/health`가 HTML이나 404 대신 JSON 200, 비로그인 `/api/v1/auth/me`가 404 대신 401, 실제 회원가입과 로그인 유지가 정상인지 확인한다. 프록시와 CORS만 고친 상태로 최신 로그인 배포가 완료되었다고 보고하지 않는다.

이번 진단에서는 원격 환경변수 변경·Git push·Vercel/Render 재배포를 수행하지 않았다. 로컬 프록시 설정은 준비되어 있으나 실제 배포 반영은 남아 있다.

참고: [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [Vercel 배포 환경](https://vercel.com/docs/deployments/environments), [Render 환경변수 반영](https://render.com/docs/configure-environment-variables).
