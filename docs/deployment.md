# 배포 기록

사용자 선택: `G.H. Byeon's Workspace`에 새 프로젝트용 서비스 생성, 외부 키 설정 전 샘플 체험용 배포.

현재 로컬 검증:

- 백엔드 pytest 25개 통과
- React/Vite 프로덕션 빌드 통과
- 7개 고정 합성 시나리오: 성찰 OFF 기대 결과 4/7, ON 7/7
- 실제 API·Supabase·OpenAI·Discord·카카오 연동은 키 설정 후 별도 검증 필요

배포 대상: `codex/meet-again-demo` 브랜치. main과 기존 다른 프로젝트 서비스는 변경하지 않았습니다.

| 서비스 | 주소 | Render ID |
| --- | --- | --- |
| React 화면 | https://meet-again-ghbye-demo.onrender.com | srv-dbnkahbl550s73ff5cug |
| FastAPI | https://meet-again-ghbye-api.onrender.com | srv-dbnk8hqjnfac73ckg0mg |
| API 문서 | https://meet-again-ghbye-api.onrender.com/docs | 위 API 서비스 |

초기 배포는 두 서비스 모두 `live`로 확인했으며 공개 프론트엔드 HTTP 200과 API `/api/v1/health`의 샘플 모드 응답을 확인했습니다. 후속 변경은 같은 브랜치에서 배포하며 최종 확인 결과는 아래에 추가합니다.

로컬 Brave headless 브라우저에서 검색 → 후보 3건 → 상세·점수 → 조건 저장 → 불러오기 → 누락 조건 질문 → 보완 후 검색을 확인했습니다. 390px 모바일 화면의 가로 넘침과 페이지 JavaScript 오류가 없었습니다. 카카오 실제 지도·Discord 실제 수신은 이 검증에 포함되지 않습니다.

샘플 환경은 SQLite 임시 기록을 사용하며 재시작·재배포 시 사라질 수 있습니다. 실제 서비스의 영속 저장은 Supabase 연결 후에만 보장할 수 있습니다. 문자·브라우저 푸시·자동 신규 공고 감지·중간 노드 내구성 재개는 구현되지 않았습니다.
