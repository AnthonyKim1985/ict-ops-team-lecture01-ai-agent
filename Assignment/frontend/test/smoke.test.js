import { describe, expect, it } from "vitest";

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
