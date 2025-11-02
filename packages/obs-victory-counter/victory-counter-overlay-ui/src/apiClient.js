const DEFAULT_BASE_URL = "http://127.0.0.1:8912";

const ensureOk = async (response) => {
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload && payload.error) {
        message += `: ${payload.error}`;
      }
    } catch {
      // パースに失敗した場合は詳細メッセージなしで扱う
    }
    throw new Error(message);
  }
  return response.json();
};

export const createApiClient = ({ baseUrl = DEFAULT_BASE_URL, fetchFn = globalThis.fetch } = {}) => {
  if (typeof fetchFn !== "function") {
    throw new TypeError("fetchFn must be a function");
  }

  const buildUrl = (path) => `${baseUrl.replace(/\/$/, "")}${path}`;

  return {
    async fetchState() {
      const response = await fetchFn(buildUrl("/state"));
      return ensureOk(response);
    },

    async fetchHistory(limit = 5) {
      const response = await fetchFn(buildUrl(`/history?limit=${encodeURIComponent(limit)}`));
      return ensureOk(response);
    },

    async postAdjust(payload) {
      const response = await fetchFn(buildUrl("/adjust"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      return ensureOk(response);
    },
  };
};

export const apiClient = createApiClient();
