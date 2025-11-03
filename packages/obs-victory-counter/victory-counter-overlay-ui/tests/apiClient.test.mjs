import test from 'node:test';
import assert from 'node:assert';

import { createApiClient } from '../src/apiClient.js';

test('fetchState issues GET request to /state', async () => {
  const requests = [];
  const client = createApiClient({
    baseUrl: 'http://example.test',
    fetchFn: async (url, options = {}) => {
      requests.push({ url, options });
      return {
        ok: true,
        status: 200,
        json: async () => ({ victories: 1, defeats: 2, draws: 1, total: 4, results: [], adjustments: [] }),
      };
    },
  });

  const response = await client.fetchState();
  assert.strictEqual(requests[0].url, 'http://example.test/state');
  assert.strictEqual(requests[0].options?.method ?? 'GET', 'GET');
  assert.strictEqual(response.draws, 1);
  assert.strictEqual(response.total, 4);
});

test('postAdjust sends payload as JSON', async () => {
  let captured;
  const client = createApiClient({
    baseUrl: 'http://example.test',
    fetchFn: async (url, options = {}) => {
      captured = { url, options };
      return {
        ok: true,
        status: 202,
        json: async () => ({ event: { value: 'victory', delta: 2 } }),
      };
    },
  });

  await client.postAdjust({ value: 'victory', delta: 2 });
  assert.strictEqual(captured.url, 'http://example.test/adjust');
  assert.strictEqual(captured.options.method, 'POST');
  assert.strictEqual(JSON.parse(captured.options.body).delta, 2);
  assert.strictEqual(captured.options.headers['Content-Type'], 'application/json');
});

test('fetchHistory propagates HTTP errors', async () => {
  const client = createApiClient({
    baseUrl: 'http://example.test',
    fetchFn: async () => ({
      ok: false,
      status: 500,
      json: async () => ({ error: 'internal_server_error' }),
    }),
  });

  await assert.rejects(client.fetchHistory(), /500/);
});
