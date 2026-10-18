import { describe, expect, it } from "vitest";
import { posterior, softmax } from "./study-experiments";

describe("numerical experiments", () => {
  it("normalizes large logits without overflow and preserves shift invariance", () => {
    const result = softmax([10000, 10001, 10002], 1);
    expect(result.reduce((a, b) => a + b, 0)).toBeCloseTo(1);
    result.forEach((v, i) => expect(v).toBeCloseTo(softmax([0, 1, 2], 1)[i]));
  });
  it("flattens probabilities at higher temperature", () => {
    expect(softmax([0, 1, 2], 3)[2]).toBeLessThan(softmax([0, 1, 2], 0.2)[2]);
    expect(() => softmax([1], 0)).toThrow();
  });
  it("accounts for base rates and an impossible conditioning event", () => {
    expect(posterior(0.01, 0.9, 0.1)).toBeCloseTo(0.083333);
    expect(posterior(0, 0, 0)).toBeNull();
    expect(() => posterior(2, 0.5, 0.5)).toThrow();
  });
});
