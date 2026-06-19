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
