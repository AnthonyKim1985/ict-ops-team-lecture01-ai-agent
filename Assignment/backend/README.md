# 백엔드 (날씨 AI Agent)

FastAPI + LangGraph(Claude Haiku) + Open-Meteo.

## 설치

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
```

## 환경변수

- 키는 저장소 루트 `lecture01_ai_agent/.env`의 `CLAUDE_API_KEY`를 사용한다.
- `src/config.py`가 이를 SDK 표준 `ANTHROPIC_API_KEY`로 브릿지한다(코드/.env 수정 불필요).

## 실행

```bash
uvicorn src.main:app --reload --port 8000
```

## 테스트

```bash
pytest -v
```

외부 API/LLM은 모두 mock 처리되어 키 없이도 통과해야 한다.

## 엔드포인트

- `GET /health` -> `{"status":"ok"}`
- `POST /chat` body `{"message": "..."}` -> `{"reply": "..."}`
