#!/usr/bin/env bash
# 날씨 AI Agent 로컬 실행 스크립트
# 백엔드(FastAPI, :8000)와 프론트엔드(정적 서버, :5500)를 함께 기동한다.
# Ctrl+C 한 번으로 두 프로세스를 모두 종료한다.
set -euo pipefail

# 스크립트 위치를 기준으로 경로를 잡아 어느 디렉터리에서 실행해도 동작하게 한다.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_SRC="$SCRIPT_DIR/frontend/src"
VENV_DIR="$BACKEND_DIR/.venv"
ENV_FILE="$SCRIPT_DIR/../.env"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5500}"

# 프론트 정적 서버에 쓸 파이썬 인터프리터(시스템 python3 우선).
PYTHON_BIN="$(command -v python3 || command -v python)"

# --- .env 안내 (없어도 기동은 되지만 실제 /chat 호출에는 키가 필요) ---
if [[ ! -f "$ENV_FILE" ]]; then
  echo "⚠️  $ENV_FILE 가 없습니다. /health 와 프론트는 뜨지만 실제 /chat 응답에는 CLAUDE_API_KEY가 필요합니다."
fi

# --- 백엔드 가상환경 준비 ---
if [[ ! -d "$VENV_DIR" ]]; then
  echo "📦 백엔드 가상환경이 없어 생성합니다: $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -e "$BACKEND_DIR[test]"
fi
VENV_PYTHON="$VENV_DIR/bin/python"

# --- 종료 처리: 백그라운드 프로세스 트리 정리 ---
# uvicorn --reload 는 리로더+워커 2개 프로세스를 띄우므로 자식까지 재귀로 정리한다.
kill_tree() {
  local pid="$1"
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null); do
    kill_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

PIDS=()
CLEANED=0
cleanup() {
  [[ "$CLEANED" -eq 1 ]] && return
  CLEANED=1
  echo
  echo "🛑 종료 중..."
  for pid in "${PIDS[@]}"; do
    kill_tree "$pid"
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# --- 백엔드 기동 (cwd=backend 이어야 src 패키지 import 가능) ---
echo "🚀 백엔드 기동: http://localhost:$BACKEND_PORT (docs: /docs)"
(
  cd "$BACKEND_DIR"
  exec "$VENV_PYTHON" -m uvicorn src.main:app --reload --port "$BACKEND_PORT"
) &
PIDS+=($!)

# --- 프론트엔드 기동 (정적 서버) ---
echo "🌐 프론트엔드 기동: http://localhost:$FRONTEND_PORT"
(
  exec "$PYTHON_BIN" -m http.server "$FRONTEND_PORT" --directory "$FRONTEND_SRC"
) &
PIDS+=($!)

echo
echo "✅ 실행 완료. 브라우저에서 http://localhost:$FRONTEND_PORT 접속 → \"내일 서울 날씨 어때?\""
echo "   (Ctrl+C 로 두 서버를 함께 종료)"
echo

# 둘 중 하나라도 끝나면 스크립트도 종료 → trap이 나머지를 정리.
# (macOS 기본 bash 3.2 호환: `wait -n` 대신 PID 생존 폴링)
while :; do
  for pid in "${PIDS[@]}"; do
    kill -0 "$pid" 2>/dev/null || exit 0
  done
  sleep 1
done
