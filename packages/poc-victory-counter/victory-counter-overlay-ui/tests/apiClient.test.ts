import test from "node:test";
import assert from "node:assert";

import { createApiClient } from "../src/apiClient";

test("fetchState issues GET request to /state", async () => {
  const requests: Array<{ url: string; options?: RequestInit }> = [];
  const client = createApiClient({
    baseUrl: "http://example.test",
    fetchFn: async (url, options = {}) => {
      requests.push({ url: String(url), options });
      return {
        ok: true,
        status: 200,
        json: async () => ({ victories: 1, defeats: 2, draws: 1, total: 4, results: [], adjustments: [] }),
      } as Response;
    },
  });

  const response = await client.fetchState();
  assert.strictEqual(requests[0]?.url, "http://example.test/state");
  assert.strictEqual(requests[0]?.options?.method ?? "GET", "GET");
  assert.strictEqual(response.draws, 1);
  assert.strictEqual(response.total, 4);
});

test("postAdjust sends payload as JSON", async () => {
  let captured: { url: string; options?: RequestInit } | undefined;
  const client = createApiClient({
    baseUrl: "http://example.test",
    fetchFn: async (url, options = {}) => {
      captured = { url: String(url), options };
      return {
        ok: true,
        status: 202,
        json: async () => ({ event: { value: "victory", delta: 2 } }),
      } as Response;
    },
  });

  await client.postAdjust({ value: "victory", delta: 2 });
  assert.strictEqual(captured?.url, "http://example.test/adjust");
  assert.strictEqual(captured?.options?.method, "POST");
  assert.strictEqual(JSON.parse(String(captured?.options?.body)).delta, 2);
  const headers = captured?.options?.headers;
  assert.ok(headers);
  const contentType = headers instanceof Headers
    ? headers.get("Content-Type")
    : Array.isArray(headers)
      ? headers.find(([key]) => key.toLowerCase() === "content-type")?.[1]
      : (headers as Record<string, string>)["Content-Type"] ?? (headers as Record<string, string>)["content-type"];
  assert.strictEqual(contentType, "application/json");
});

test("fetchHistory propagates HTTP errors", async () => {
  const client = createApiClient({
    baseUrl: "http://example.test",
    fetchFn: async () => ({
      ok: false,
      status: 500,
      json: async () => ({ error: "internal_server_error" }),
    } as Response),
  });

  await assert.rejects(client.fetchHistory(), /500/);
});
