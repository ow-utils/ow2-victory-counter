import "./style.css";
import {
  apiClient,
  createApiClient,
  type StateEvent,
  type StateResponse,
} from "../apiClient";

const DEFAULT_HISTORY_LIMIT = 5;
const DEFAULT_POLL_SECONDS = 5;

const params = new URLSearchParams(window.location.search);
const theme = params.get("theme")?.toLowerCase() ?? "dark";
const historyLimit = Math.max(
  1,
  Number.parseInt(params.get("history") ?? `${DEFAULT_HISTORY_LIMIT}`, 10) ||
    DEFAULT_HISTORY_LIMIT,
);
const pollSeconds = Math.max(
  1,
  Math.min(
    60,
    Number.parseInt(params.get("poll") ?? `${DEFAULT_POLL_SECONDS}`, 10) ||
      DEFAULT_POLL_SECONDS,
  ),
);
const showDraw = (params.get("showDraw") ?? "true").toLowerCase() !== "false";
const baseUrl = params.get("api") ?? undefined;

const client = baseUrl ? createApiClient({ baseUrl }) : apiClient;

const body = document.body;
body.classList.add(
  "overlay-body",
  `overlay-theme--${["dark", "light", "transparent"].includes(theme) ? theme : "dark"}`,
);
body.style.transform = `scale(${Math.max(0.5, Math.min(2, Number.parseFloat(params.get("scale") ?? "1")))})`;

const root = document.getElementById("overlay-root");

const summaryEl = document.createElement("div");
summaryEl.className = "overlay-summary";
summaryEl.innerHTML = `
  <div class="overlay-card overlay-card--victory">
    <span class="overlay-card__label">Victory</span>
    <span id="overlay-count-victory" class="overlay-card__value">0</span>
  </div>
  <div class="overlay-card overlay-card--defeat">
    <span class="overlay-card__label">Defeat</span>
    <span id="overlay-count-defeat" class="overlay-card__value">0</span>
  </div>
  ${
    showDraw
      ? '<div class="overlay-card overlay-card--draw"><span class="overlay-card__label">Draw</span><span id="overlay-count-draw" class="overlay-card__value">0</span></div>'
      : ""
  }
`;

const historyList = document.createElement("ul");
historyList.id = "overlay-history";
historyList.className = "overlay-history";
historyList.innerHTML =
  "<li class='overlay-history__item overlay-history__item--draw'><span class='overlay-history__value'>Loading...</span></li>";

if (root) {
  root.className = "overlay-root";
  root.append(summaryEl, historyList);
} else {
  body.append(summaryEl, historyList);
}

const elements = {
  victory: document.getElementById("overlay-count-victory"),
  defeat: document.getElementById("overlay-count-defeat"),
  draw: document.getElementById("overlay-count-draw"),
  history: historyList,
};

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleTimeString([], { hour12: false });
};

const renderSummary = (payload: StateResponse): void => {
  if (elements.victory) {
    elements.victory.textContent = String(payload.victories ?? 0);
  }
  if (elements.defeat) {
    elements.defeat.textContent = String(payload.defeats ?? 0);
  }
  if (elements.draw) {
    elements.draw.textContent = String(payload.draws ?? 0);
  }
};

const renderHistory = (events: StateEvent[]): void => {
  elements.history.innerHTML = "";
  const items = events.slice(-historyLimit).reverse();
  if (!items.length) {
    elements.history.innerHTML =
      "<li class='overlay-history__item overlay-history__item--draw'><span class='overlay-history__value'>NO DATA</span></li>";
    return;
  }
  for (const event of items) {
    const li = document.createElement("li");
    const value = (event.value || "draw").toLowerCase();
    li.className = `overlay-history__item overlay-history__item--${value}`;

    const timeEl = document.createElement("span");
    timeEl.className = "overlay-history__time";
    timeEl.textContent = formatTime(event.timestamp);
    li.appendChild(timeEl);

    const valueEl = document.createElement("span");
    valueEl.className = "overlay-history__value";
    valueEl.textContent = ((event.value || "") + "").toUpperCase();
    li.appendChild(valueEl);

    const deltaEl = document.createElement("span");
    deltaEl.className = "overlay-history__delta";
    const delta = Number(event.delta ?? 0);
    deltaEl.textContent = delta > 0 ? "+" + delta : String(delta);
    li.appendChild(deltaEl);

    if (event.note) {
      const noteEl = document.createElement("span");
      noteEl.className = "overlay-history__note";
      noteEl.textContent = event.note;
      li.appendChild(noteEl);
    }

    elements.history.appendChild(li);
  }
};

const refresh = async () => {
  try {
    const [summaryPayload, historyPayload] = await Promise.all([
      client.fetchState(),
      client.fetchHistory(historyLimit),
    ]);
    renderSummary(summaryPayload);
    renderHistory(historyPayload.events ?? []);
  } catch (error) {
    console.error("overlay refresh failed", error);
  }
};

void refresh();
setInterval(() => {
  void refresh();
}, pollSeconds * 1000);
