# TASK-0: 프로젝트 스캐폴딩

> **시작 브랜치:** `chore/scaffolding` (예: `git switch main && git pull && git switch -c chore/scaffolding`)
> **이 문서만 보고 개발할 수 있도록 구성됨.** 외부 문서 참조는 맨 아래 "참조" 절에만 표시.

## 목표

날씨 AI Agent의 **빈 골격**을 만든다. 이 태스크가 끝나면:
- 백엔드는 `pip install -e .` 후 `uvicorn src.main:app`으로 기동되고 `GET /health`가 응답한다.
- `pytest`가 통과(헬스 스모크 + config import)하고, 프론트엔드 `npx vitest run`이 스모크 테스트를 통과한다.
- 이후 태스크(TASK-1~5)가 파일을 채워 넣을 디렉터리/설정/테스트 부트스트랩이 모두 준비된다.

## 배경 (프로젝트 한 줄 요약)

사용자가 도시명을 말하면 **내일 날씨**를 한 문장으로 답하는 에이전트. 백엔드는 Python + FastAPI + LangGraph(Claude Haiku가 날씨 도구 호출), 프론트엔드는 Vanilla SPA 채팅창. 과제 제약상 **`src` 폴더에는 테스트 코드를 절대 두지 않고**, 모든 테스트는 `backend/test`, `frontend/test`에 둔다.

## 만들 디렉터리/파일 (정확한 경로)

```
Assignment/
├── .gitignore                          ← 신규
├── backend/
│   ├── pyproject.toml                  ← 신규 (의존성 + pytest 설정)
│   ├── src/
│   │   ├── __init__.py                 ← 신규 (빈 파일)
│   │   ├── config.py                   ← 신규 (env 브릿지 + 설정)
│   │   └── main.py                     ← 신규 (최소: /health 만. TASK-3에서 /chat 추가)
│   └── test/
│       ├── conftest.py                 ← 신규 (테스트 전 더미 키 주입 — 매우 중요)
│       └── test_health.py              ← 신규 (스모크)
└── frontend/
    ├── package.json                    ← 신규
    ├── vitest.config.js                ← 신규
    ├── src/
    │   └── .gitkeep                     ← 신규 (TASK-4가 채움)
    └── test/
        └── smoke.test.js               ← 신규 (스모크. TASK-4가 app.test.js 추가)
```

> 참고: `backend/src/weather.py`, `backend/src/agent.py`는 **이 태스크에서 만들지 않는다** (각각 TASK-1, TASK-2 담당). `main.py`는 여기서 `/health`만 만들고 TASK-3이 `/chat`·CORS를 추가한다.

---

## 단계별 작업 (TDD: 가능한 곳은 실패 테스트 → 구현 → 통과)

### Step 1: 디렉터리 생성

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent/Assignment
mkdir -p backend/src backend/test frontend/src frontend/test
touch backend/src/__init__.py frontend/src/.gitkeep
```

### Step 2: `Assignment/.gitignore` 작성

> `.env`는 이미 git 루트(`lecture01_ai_agent/.gitignore`)에서 무시되고 있다. 여기서는 Python/Node 빌드 산출물만 무시한다.

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/
.pytest_cache/

# Node
node_modules/

# OS
.DS_Store
```

### Step 3: `backend/pyproject.toml` 작성

> **이 10여 줄이 TASK-0에서 가장 깨지기 쉽다.** `hatchling`이 `src`를 패키지로 빌드하고, pytest는 `pythonpath=["."]`로 `src`를 import 가능하게 만든다. 그대로 작성할 것.

```toml
[project]
name = "weather-agent-backend"
version = "0.1.0"
description = "날씨 AI Agent backend"
requires-python = ">=3.10"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "langgraph",
  "langchain-anthropic",
  "langchain-core",
  "httpx",
  "pydantic",
  "pydantic-settings",
  "python-dotenv",
]

[project.optional-dependencies]
test = [
  "pytest",
  "pytest-asyncio",
  "pytest-httpx",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
pythonpath = ["."]
asyncio_mode = "auto"
testpaths = ["test"]
```

> **버전 핀(pin):** 위 의존성은 버전 미지정 상태다. 설치 직후 `langchain-langgraph` 계열은 **반드시 `langchain-dependencies` 스킬을 호출해 현재 권장 안정 버전으로 핀**할 것 (참조 절). 최소한 `langgraph`, `langchain-anthropic`, `langchain-core` 3종은 호환 버전으로 맞춘다.

### Step 4: `backend/src/config.py` 작성 (env 브릿지)

> **핵심 이슈:** `.env`에는 키가 **`CLAUDE_API_KEY`**로 저장돼 있으나 Anthropic SDK 기본값은 **`ANTHROPIC_API_KEY`**다. `.env` 경로는 CWD에 의존하지 않도록 `config.py` 파일 위치 기준으로 계산한다(`parents[3]` = git 루트 `lecture01_ai_agent/`).

```python
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py 위치: Assignment/backend/src/config.py
#   parents[0]=src, [1]=backend, [2]=Assignment, [3]=lecture01_ai_agent (.env 위치)
ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(ENV_PATH)

# 환경변수 브릿지: .env의 CLAUDE_API_KEY → SDK 표준 ANTHROPIC_API_KEY
# CLAUDE_API_KEY가 없을 수도 있으므로 반드시 가드한다 (없으면 KeyError 발생).
if "CLAUDE_API_KEY" in os.environ:
    os.environ.setdefault("ANTHROPIC_API_KEY", os.environ["CLAUDE_API_KEY"])


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str = ""          # 환경에서 자동 주입(없어도 import는 성공)
    model_name: str = "claude-haiku-4-5"  # Claude Haiku (과제 지정)
    request_timeout_seconds: float = 10.0  # Open-Meteo httpx 타임아웃


settings = Settings()
```

### Step 5: `backend/test/conftest.py` 작성 (⚠️ 매우 중요 — import 크래시 방지)

> **왜 필요한가:** TASK-2의 `agent.py`는 모듈 로드 시 `ChatAnthropic(...)`를 생성한다. 키가 전혀 없는 환경(CI 등)에서는 **import 시점에** 예외가 나 모든 테스트 수집이 실패할 수 있다. 어떤 src import보다 먼저 더미 키를 넣어 둔다. `ChatAnthropic`은 생성 시 키를 보관만 하고 실제 호출(invoke) 전까지 네트워크를 쓰지 않으므로 더미로 충분하다.

```python
import os

# 어떤 src import보다 먼저 실행되어야 한다(conftest.py는 pytest가 가장 먼저 로드).
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-dummy-for-tests")
```

### Step 6: `backend/src/main.py` 작성 (최소 골격 — /health 만)

```python
from fastapi import FastAPI

from src.config import settings  # import 검증 겸 설정 로드

app = FastAPI(title="날씨 AI Agent")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

> TASK-3이 이 파일에 `POST /chat`, `CORSMiddleware`, Pydantic 요청/응답 모델을 추가한다. `/health`는 유지한다.

### Step 7: `backend/test/test_health.py` 작성 (스모크)

```python
import httpx
import pytest
from httpx import ASGITransport

from src.main import app


@pytest.mark.asyncio
async def test_config_imports():
    # config 모듈이 정상 로드되고 모델명이 기대값인지
    from src.config import settings
    assert settings.model_name == "claude-haiku-4-5"


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

### Step 8: 백엔드 설치 및 검증

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent/Assignment/backend
python -m venv .venv && source .venv/bin/activate   # 권장(가상환경)
pip install -e ".[test]"
python -c "import src.config; print('config OK')"   # 기대: config OK
pytest -v                                            # 기대: 2 passed
uvicorn src.main:app --port 8000 &                   # 기동 확인
sleep 2 && curl -s http://localhost:8000/health      # 기대: {"status":"ok"}
kill %1
```

### Step 9: `frontend/package.json` 작성

```json
{
  "name": "weather-agent-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run"
  }
}
```

### Step 10: `frontend/vitest.config.js` 작성

```javascript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["test/**/*.test.js"],
  },
});
```

### Step 11: `frontend/test/smoke.test.js` 작성 (스모크)

```javascript
import { describe, it, expect } from "vitest";

describe("toolchain smoke", () => {
  it("runs vitest", () => {
    expect(1 + 1).toBe(2);
  });

  it("has jsdom document", () => {
    const el = document.createElement("div");
    el.textContent = "hi";
    expect(el.textContent).toBe("hi");
  });
});
```

### Step 12: 프론트엔드 설치 및 검증

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent/Assignment/frontend
npm install -D vitest jsdom    # 최신 안정 버전 설치 + package.json에 기록
npx vitest run                 # 기대: 2 passed (smoke)
```

### Step 13: 커밋

```bash
cd /Users/anthonykim/Workspace/SlideWorkspace/lecture01_ai_agent/Assignment
git add .gitignore backend frontend
git commit -m "chore: 프로젝트 스캐폴딩 (백엔드/프론트엔드 골격, config env 브릿지, 테스트 부트스트랩)"
```

---

## 완료 기준 (Definition of Done)

- [ ] `backend/`에서 `pip install -e ".[test]"` 성공
- [ ] `python -c "import src.config"` 성공
- [ ] `pytest` → 2 passed (config import, /health)
- [ ] `uvicorn src.main:app` 기동 후 `GET /health` → `{"status":"ok"}`
- [ ] `frontend/`에서 `npm install -D vitest jsdom` 후 `npx vitest run` → 2 passed
- [ ] `.gitignore`에 Python/Node 산출물 포함
- [ ] 커밋 완료

## 다음 태스크에 넘기는 인터페이스 (다운스트림이 의존)

- `src.config.settings` — `.model_name="claude-haiku-4-5"`, `.request_timeout_seconds=10.0`, 그리고 import 시 `ANTHROPIC_API_KEY` 환경변수 보장(`.env`의 `CLAUDE_API_KEY` 브릿지).
- `backend/test/conftest.py` — 테스트 시 더미 `ANTHROPIC_API_KEY` 주입(TASK-2/TASK-3가 의존).
- `src.main:app` — FastAPI 앱(현재 `/health`만). TASK-3가 `/chat`·CORS 확장.
- pytest 설정: `pythonpath=["."]`, `asyncio_mode="auto"` → 테스트에서 `from src.x import ...` 및 `async def test_...` 사용 가능.

---

## 참조 (외부 문서/스킬 — 필요 시에만)

- **`langchain-dependencies` 스킬** — Step 3에서 `langgraph`/`langchain-anthropic`/`langchain-core` 버전 핀. (필수 호출)
- `ASSIGNMENT.md` — 과제 원문 제약(`src`에 테스트 금지, backend/frontend 경로 규칙).
- `PLAN.md` §4(디렉터리 구조), §5.4(설정/env 브릿지), §8(의존성). 본 문서가 해당 내용을 모두 포함하므로 보충용.
