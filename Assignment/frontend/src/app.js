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

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
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
    } catch {
      loading.remove();
      messages.appendChild(
        renderMessage("앗, 응답을 받지 못했어요. 잠시 후 다시 시도해 주세요.", "bot"),
      );
    }

    messages.scrollTop = messages.scrollHeight;
  });
}
