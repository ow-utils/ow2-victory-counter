const DEFAULT_BASE_URL = "http://127.0.0.1:8912";

type FetchFn = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface StateEvent {
  type: "result" | "adjustment";
  value: "victory" | "defeat" | "draw";
  delta: number;
  timestamp: string;
  confidence?: number;
  note?: string;
}

export interface StateResponse {
  victories?: number;
  defeats?: number;
  draws?: number;
  total?: number;
  results?: StateEvent[];
  adjustments?: StateEvent[];
}

export interface HistoryResponse {
  events?: StateEvent[];
}

export interface AdjustmentPayload {
  value: "victory" | "defeat" | "draw";
  delta: number;
  note?: string;
}

const ensureOk = async (response: Response): Promise<any> => {
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

interface ApiClientInit {
  baseUrl?: string;
  fetchFn?: FetchFn;
}

export const createApiClient = ({
  baseUrl = DEFAULT_BASE_URL,
  fetchFn = globalThis.fetch as FetchFn,
}: ApiClientInit = {}) => {
  if (typeof fetchFn !== "function") {
    throw new TypeError("fetchFn must be a function");
  }

  const buildUrl = (path: string) => `${baseUrl.replace(/\/$/, "")}${path}`;

  return {
    async fetchState(): Promise<StateResponse> {
      const response = await fetchFn(buildUrl("/state"));
      return ensureOk(response) as Promise<StateResponse>;
    },

    async fetchHistory(limit = 5): Promise<HistoryResponse> {
      const response = await fetchFn(buildUrl(`/history?limit=${encodeURIComponent(limit)}`));
      return ensureOk(response) as Promise<HistoryResponse>;
    },

    async postAdjust(payload: AdjustmentPayload): Promise<StateEvent> {
      const response = await fetchFn(buildUrl("/adjust"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const data = await ensureOk(response);
      return data.event as StateEvent;
    },
  };
};

export const apiClient = createApiClient();
