# 날씨 AI Agent 개발

## 아키텍처
- Python FastAPI 기반 Backend, Frontend간 통신
- Backend는 LangGraph 기반으로 구현, 날씨 정보는 Skill을 통해 구현하여 클로드 Haiku가 호출하도록 구성
- Frontend는 간단한 채팅창이 있는 Single Page로 구성
- Backend 코드 및 테스트 경로는 각각 backend/src, backend/test에서 진행
- Frontend 코드 및 테스트 경로는 각각 frontend/src, frontend/test에서 진행
- **src 폴더에 절대 test 코드 작성하지마**

## 목표
- “날씨 에이전트”를 만들어 줘. 사용자가 도시 이름을 말하면 그 도시의 내일 날씨를 알려주는 프로그램이야.

## 도구
- 인터넷 날씨 검색 API를 사용해서 (도시 이름 → 기온·강수 정보)를 가져와.

## 행동
- ① 질문에서 도시 이름 찾기 → ② 날씨 도구 호출 → ③ 결과를 한 문장으로 정리 → ④ 우산이 필요하면 한마디 덧붙이기

## 출력 예시
- “내일 서울은 12°C에 비가 와요. 우산 챙기세요! ☂️”
