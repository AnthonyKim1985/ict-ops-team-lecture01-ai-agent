# TASK-4: 프론트엔드 채팅 UI — `index.html` / `app.js` / `styles.css`

> **시작 브랜치:** `feat/frontend-chat` (TASK-3 머지 후 `git switch -c feat/frontend-chat`)
> **이 문서만 보고 개발할 수 있도록 구성됨.** 외부 참조는 맨 아래 "참조" 절에만.

## 선행 작업 (TASK-0 · TASK-3 산출물 — 이미 존재해야 함)

- **`frontend/package.json`** (TASK-0): `"type": "module"`, `scripts.test = "vitest run"`, devDeps에 `vitest`/`jsdom`.
- **`frontend/vitest.config.js`** (TASK-0): `environment: "jsdom"`, `include: ["test/**/*.test.js"]`.
- **`frontend/test/smoke.test.js`** (TASK-0): 스모크 테스트(이 태스크에서 **삭제**하고 `app.test.js`로 대체).
- **백엔드 `/chat` 계약** (TASK-3): `POST http://localhost:8000/chat`, body `{"message": string}` → `{"reply": string}`. CORS로 localhost 허용됨.

## 목표

단일 페이지 채팅 UI. 입력 → `POST /chat` → `reply`를 말풍선으로 렌더. 로딩("생각 중...") 표시, 에러 핸들링. **렌더링/통신 로직을 테스트 가능한 순수 함수**(`renderMessage`, `sendMessage`)로 분리하고 Vitest로 검증.

## 만들/수정 파일

```
frontend/src/index.html        ← 신규
frontend/src/app.js            ← 신규 (ESM, 순수 함수 export + initChat)
frontend/src/styles.css        ← 신규
frontend/test/app.test.js      ← 신규 (테스트 — src에 두지 말 것)
frontend/test/smoke.test.js    ← 삭제 (TASK-0 스모크 대체)
frontend/src/.gitkeep          ← 삭제 (실제 파일 생겼으므로)
```

## 공개 인터페이스 (테스트가 의존)

- `renderMessage(text: string, sender: "user"|"bot"|"loading"): HTMLElement` — 말풍선 DOM 노드 생성/반환.
- `sendMessage(message: string, opts?): Promise<string>` — `/chat` 호출 후 `reply` 반환. `opts.fetchFn`(기본 전역 `fetch`), `opts.endpoint`(기본 `http://localhost:8000/chat`) 주입 가능. 응답이 `!ok`면 throw.
- `initChat(root?: Document)` — DOM 이벤트 와이어링(폼 submit → sendMessage → 렌더). `index.html`이 호출.

---

## 단계별 작업 (TDD)

### Step 1: 실패 테스트 작성 — `frontend/test/app.test.js`

```javascript
import { describe, it, expect, vi } from "vitest";
import { renderMessage, sendMessage } from "../src/app.js";

describe("renderMessage", () => {
  it("사용자 메시지 말풍선을 만든다", () => {
    const el = renderMessage("안녕", "user");
    expect(el.textContent).toBe("안녕");
    expect(el.classList.contains("message")).toBe(true);
    expect(el.classList.contains("user")).toBe(true);
  });

  it("봇 메시지 말풍선을 만든다", () => {
    const el = renderMessage("내일 서울은 맑아요.", "bot");
    expect(el.classList.contains("bot")).toBe(true);
  });
});

describe("sendMessage", () => {
  it("reply 텍스트를 반환한다", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ reply: "내일 서울은 12°C에 비가 와요. ☂️" }),
    });

    const reply = await sendMessage("내일 서울 날씨", { fetchFn: fakeFetch });

    expect(reply).toBe("내일 서울은 12°C에 비가 와요. ☂️");
    expect(fakeFetch).toHaveBeenCalledOnce();
    const [, options] = fakeFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ message: "내일 서울 날씨" });
  });

  it("응답이 ok가 아니면 throw 한다", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({ ok: false, status: 500 });
    await expect(sendMessage("x", { fetchFn: fakeFetch })).rejects.toThrow();
  });
});
```

### Step 2: 스모크 테스트 제거 후 실패 확인

```bash
cd frontend
rm -f test/smoke.test.js src/.gitkeep
npx vitest run
```
기대: `../src/app.js`를 찾지 못해 실패.

### Step 3: 구현 — `frontend/src/app.js`

```javascript
const DEFAULT_ENDPOINT = "http://localhost:8000/chat";

export function renderMessage(text, sender) {
  const div = document.createElement("div");
  div.className = `message ${sender}`;
  div.textContent = text;
  return div;
}

export async function sendMessage(message, opts = {}) {
  const { endpoint = DEFAULT_ENDPOINT, fetchFn = fetch } = opts;
  const res = await fetchFn(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    throw new Error(`서버 오류: ${res.status}`);
  }
  const data = await res.json();
  return data.reply;
}

export function initChat(root = document) {
  const form = root.getElementById("chat-form");
  const input = root.getElementById("chat-input");
  const messages = root.getElementById("messages");
  if (!form || !input || !messages) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    messages.appendChild(renderMessage(text, "user"));
    input.value = "";

    const loading = renderMessage("생각 중...", "loading");
    messages.appendChild(loading);
    messages.scrollTop = messages.scrollHeight;

    try {
      const reply = await sendMessage(text);
      loading.remove();
      messages.appendChild(renderMessage(reply, "bot"));
    } catch (err) {
      loading.remove();
      messages.appendChild(
        renderMessage("앗, 응답을 받지 못했어요. 잠시 후 다시 시도해 주세요.", "bot")
      );
    }
    messages.scrollTop = messages.scrollHeight;
  });
}
```

### Step 4: 구현 — `frontend/src/index.html`

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>날씨 AI Agent</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main class="chat">
    <header class="chat-header">☀️ 날씨 비서</header>
    <div id="messages" class="messages"></div>
    <form id="chat-form" class="input-bar">
      <input id="chat-input" type="text" placeholder="예: 내일 서울 날씨 어때?" autocomplete="off" />
      <button type="submit">전송</button>
    </form>
  </main>
  <script type="module">
    import { initChat } from "./app.js";
    initChat();
  </script>
</body>
</html>
```

### Step 5: 구현 — `frontend/src/styles.css`

```css
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  background: #f0f2f5;
  display: flex;
  justify-content: center;
}
.chat {
  width: 100%;
  max-width: 480px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}
.chat-header {
  padding: 16px;
  font-weight: 700;
  font-size: 18px;
  background: #4a90d9;
  color: #fff;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.message {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 16px;
  line-height: 1.4;
  word-break: break-word;
}
.message.user { align-self: flex-end; background: #4a90d9; color: #fff; }
.message.bot { align-self: flex-start; background: #e9eaed; color: #1a1a1a; }
.message.loading { align-self: flex-start; background: #e9eaed; color: #888; font-style: italic; }
.input-bar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #e0e0e0;
}
.input-bar input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ccc;
  border-radius: 20px;
  font-size: 15px;
}
.input-bar button {
  padding: 10px 18px;
  border: none;
  border-radius: 20px;
  background: #4a90d9;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
```

### Step 6: 테스트 통과 확인

```bash
cd frontend && npx vitest run
```
기대: 4 passed (renderMessage 2 + sendMessage 2).

### Step 7: 커밋

```bash
git add frontend/src/index.html frontend/src/app.js frontend/src/styles.css frontend/test/app.test.js
git rm --cached frontend/test/smoke.test.js frontend/src/.gitkeep 2>/dev/null || true
git commit -m "feat: 프론트엔드 채팅 UI(순수 함수 분리) + Vitest 테스트"
```

---

## 완료 기준 (Definition of Done)

- [ ] `npx vitest run` → 4 passed
- [ ] `renderMessage`가 `message {sender}` 클래스 말풍선 생성
- [ ] `sendMessage`가 `POST /chat` 호출 후 `reply` 반환, `!ok`면 throw
- [ ] `index.html`이 `initChat()` 호출, 로딩("생각 중...")·에러 처리 포함
- [ ] `smoke.test.js`/`.gitkeep` 제거, 커밋 완료

## 다음 태스크에 넘기는 인터페이스 (TASK-5가 의존)

- 정적 서빙: `cd frontend/src && python -m http.server 5500` → 브라우저 `http://localhost:5500`.
- 프론트는 `http://localhost:8000/chat`을 호출(백엔드 기동 필요).

---

## 참조 (외부 문서/스킬 — 필요 시에만)

- `PLAN.md` §6(프론트엔드 상세), §7(프론트 테스트 전략).
- Vitest 공식 문서 — `vi.fn()` mock 패턴 확인용.
