import { apiClient } from "./apiClient.js";
import { mockTimeline, summarizeEvents } from "./mockData.js";

const root = document.getElementById("app");
const statusEl = document.getElementById("status");
const adjustForm = document.getElementById("adjust-form");
const outcomeSelect = document.getElementById("adjust-outcome");
const deltaInput = document.getElementById("adjust-delta");
const noteInput = document.getElementById("adjust-note");

const formatDelta = (delta) => (delta > 0 ? `+${delta}` : `${delta}`);

const flattenEvents = (payload) => {
  const events = [...(payload.results ?? []), ...(payload.adjustments ?? [])];
  return events
    .sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )
    .slice(-5);
};

const state = {
  status: "connecting",
  summary: summarizeEvents(mockTimeline.slice(0, 5)),
  events: mockTimeline.slice(0, 5),
};

const render = () => {
  if (!root) {
    // eslint-disable-next-line no-console
    console.warn("Root element #app が見つかりません。");
    return;
  }

  root.innerHTML = `
    <main class="overlay">
      <section class="scoreboard">
      <h1>Victory Counter</h1>
      <div class="totals">
        <div class="total victory">
          <span class="label">Victory</span>
          <span class="value">${state.summary.victories}</span>
        </div>
        <div class="total defeat">
          <span class="label">Defeat</span>
          <span class="value">${state.summary.defeats}</span>
        </div>
        <div class="total draw">
          <span class="label">Draw</span>
          <span class="value">${state.summary.draws}</span>
        </div>
        <div class="total total-matches">
          <span class="label">Total</span>
          <span class="value">${state.summary.total}</span>
        </div>
      </div>
    </section>
    <section class="history">
      <h2>Recent Events</h2>
      <ul>
        ${state.events
          .slice(-5)
          .reverse()
          .map(
            (event) => `
              <li class="${event.value}">
                <span class="timestamp">${new Date(
                  event.timestamp,
                ).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}</span>
                <span class="value">${event.value.toUpperCase()}</span>
                <span class="delta">${formatDelta(event.delta)}</span>
                ${event.note ? `<span class="note">${event.note}</span>` : ""}
              </li>
            `,
          )
          .join("")}
      </ul>
    </section>
    </main>
  `;

  if (statusEl) {
    statusEl.textContent = state.status;
  }
};

const updateFromServer = async () => {
  try {
    const payload = await apiClient.fetchState();
    const summary = {
      victories: payload.victories ?? 0,
      defeats: payload.defeats ?? 0,
      draws: payload.draws ?? 0,
      total: payload.total ?? 0,
    };
    const events = flattenEvents(payload);

    state.summary = summary;
    state.events = events;
    state.status = `Last updated: ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    // eslint-disable-next-line no-console
    console.warn("Failed to fetch /state", error);
    state.status = "Server unreachable – showing mock data.";
    if (!state.events.length) {
      state.events = mockTimeline.slice(-5);
      state.summary = summarizeEvents(state.events);
    }
  } finally {
    render();
  }
};

const startPolling = () => {
  updateFromServer();
  const interval = Number.parseInt(
    document.body.dataset.pollInterval ?? "5000",
    10,
  );
  setInterval(updateFromServer, Number.isFinite(interval) ? interval : 5000);
};

const getAdjustPayload = () => {
  const value = outcomeSelect?.value ?? "victory";
  const delta = Number.parseInt(deltaInput?.value ?? "1", 10);
  const note = noteInput?.value?.trim();
  return {
    value,
    delta: Number.isFinite(delta) ? delta : 1,
    note: note ?? "",
  };
};

const handleAdjustSubmit = async (event) => {
  event.preventDefault();
  state.status = "Sending adjustment…";
  render();

  try {
    const payload = getAdjustPayload();
    await apiClient.postAdjust(payload);
    state.status = "Adjustment accepted.";
    noteInput.value = "";
    await updateFromServer();
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Adjustment failed", error);
    state.status = `Adjustment failed: ${error?.message ?? "unknown error"}`;
    render();
  }
};

render();
startPolling();

if (adjustForm) {
  adjustForm.addEventListener("submit", handleAdjustSubmit);
}
