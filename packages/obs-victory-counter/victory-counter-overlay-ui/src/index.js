import { mockTimeline, summarizeEvents } from "./mockData.js";

const root = document.getElementById("app");

const formatDelta = (delta) => (delta > 0 ? `+${delta}` : `${delta}`);

const render = (state) => {
  if (!root) {
    // eslint-disable-next-line no-console
    console.warn("Root element #app が見つかりません。");
    return;
  }

  const summary = summarizeEvents(state.events);

  root.innerHTML = `
    <main class="overlay">
      <section class="scoreboard">
        <h1>Victory Counter (Mock)</h1>
        <div class="totals">
          <div class="total victory">
            <span class="label">Victory</span>
            <span class="value">${summary.victories}</span>
          </div>
          <div class="total defeat">
            <span class="label">Defeat</span>
            <span class="value">${summary.defeats}</span>
          </div>
          <div class="total total-matches">
            <span class="label">Total</span>
            <span class="value">${summary.total}</span>
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
                  <span class="timestamp">${new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
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
};

const state = {
  cursor: mockTimeline.length - 1,
  events: mockTimeline.slice(0, 5),
};

render(state);

setInterval(() => {
  state.cursor = (state.cursor + 1) % mockTimeline.length;
  const nextEvent = mockTimeline[state.cursor];
  state.events = [...state.events.slice(-4), nextEvent];
  render(state);
}, 2500);
