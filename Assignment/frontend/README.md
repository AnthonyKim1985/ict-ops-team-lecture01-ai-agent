# 프론트엔드 (날씨 AI Agent)

Vanilla HTML/CSS/JS 단일 페이지 채팅.

## 실행 (정적 서버)

```bash
cd frontend/src
python -m http.server 5500
```

브라우저에서 `http://localhost:5500`에 접속한다. 백엔드는 `http://localhost:8000`에서 떠 있어야 한다.

## 테스트

```bash
cd frontend
npm install
npx vitest run
```

`npm install`은 최초 1회만 필요하다.
