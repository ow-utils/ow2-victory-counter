(() => {
  const outcomeLabels = {
    victory: "Victory",
    defeat: "Defeat",
    draw: "Draw",
  };
  const previousCounters = new Map();

  const playBump = (element, outcome) => {
    if (!element || typeof element.animate !== "function") {
      return;
    }
    if (outcome === "defeat") {
      element.animate(
        [
          { transform: "translateX(0) scale(1)", filter: "drop-shadow(0 0 0 rgba(228,72,72,0))" },
          { transform: "translateX(-8px) scale(1.3)", filter: "drop-shadow(0 0 28px rgba(228,72,72,0.9)) drop-shadow(0 0 56px rgba(228,72,72,0.5))" },
          { transform: "translateX(6px) scale(1.15)", filter: "drop-shadow(0 0 18px rgba(228,72,72,0.6))" },
          { transform: "translateX(-3px) scale(1.05)", filter: "drop-shadow(0 0 8px rgba(228,72,72,0.3))" },
          { transform: "translateX(0) scale(1)", filter: "drop-shadow(0 0 0 rgba(228,72,72,0))" },
        ],
        { duration: 1200, easing: "ease-out" },
      );
    } else {
      element.animate(
        [
          { transform: "scale(1)", filter: "drop-shadow(0 0 0 rgba(249,168,37,0))" },
          { transform: "scale(1.45)", filter: "drop-shadow(0 0 32px rgba(249,168,37,0.9)) drop-shadow(0 0 60px rgba(255,255,255,0.4))" },
          { transform: "scale(0.95)", filter: "drop-shadow(0 0 14px rgba(249,168,37,0.4))" },
          { transform: "scale(1)", filter: "drop-shadow(0 0 0 rgba(249,168,37,0))" },
        ],
        { duration: 1200, easing: "cubic-bezier(.2,1.5,.4,1)" },
      );
    }
  };

  const flashPanel = (outcome) => {
    const panel = document.querySelector(".scoreboard");
    if (!panel) return;
    panel.classList.remove("flash-victory", "flash-defeat");
    void panel.offsetWidth;
    if (outcome === "victory" || outcome === "defeat") {
      const cls = `flash-${outcome}`;
      panel.classList.add(cls);
      panel.addEventListener("animationend", () => panel.classList.remove(cls), { once: true });
    }
  };

  const setText = (attrName, key, value) => {
    document.querySelectorAll(`[${attrName}="${key}"]`).forEach((element) => {
      element.textContent = value;
    });
  };

  const setCounterText = (key, value, outcome) => {
    const previousValue = previousCounters.get(key);
    document.querySelectorAll(`[data-counter="${key}"]`).forEach((element) => {
      element.textContent = value;
      if (previousValue !== undefined && previousValue !== value) {
        playBump(element, outcome);
      }
    });
    previousCounters.set(key, value);
  };

  const setWinrateWidth = (value) => {
    document
      .querySelectorAll('[data-style="winrate-width"]')
      .forEach((element) => {
        element.style.width = value;
      });
  };

  const timeFormatter = new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const formatTimestamp = (timestamp, lastOutcome) => {
    if (!lastOutcome) {
      return "Standby";
    }
    const milliseconds = Number(timestamp) * 1000;
    if (!Number.isFinite(milliseconds)) {
      return "Standby";
    }
    return `Updated ${timeFormatter.format(new Date(milliseconds))} · ${
      outcomeLabels[lastOutcome] ?? ""
    }`;
  };

  const applyCounterUpdate = (payload) => {
    const victories = Number(payload.victories ?? 0);
    const defeats = Number(payload.defeats ?? 0);
    const draws = Number(payload.draws ?? 0);
    const lastOutcome = (payload.last_outcome ?? "").toString();
    const total = victories + defeats;
    const winrate = total > 0 ? Math.round((victories / total) * 100) : 0;

    setCounterText("victories", String(victories), "victory");
    setCounterText("defeats", String(defeats), "defeat");
    setCounterText("draws", String(draws), "draw");

    if (lastOutcome) {
      flashPanel(lastOutcome);
    }
    setText("data-meta", "winrate", `${winrate}%`);
    setText(
      "data-meta",
      "last-updated",
      formatTimestamp(payload.timestamp, lastOutcome),
    );
    setText("data-meta", "last-outcome", outcomeLabels[lastOutcome] ?? "");
    setWinrateWidth(`${winrate}%`);

    document.body.dataset.lastOutcome = lastOutcome;
  };

  const fetchStatus = async () => {
    const response = await fetch("/api/status");
    if (!response.ok) {
      throw new Error(`status request failed: ${response.status}`);
    }
    applyCounterUpdate(await response.json());
  };

  const connectEvents = () => {
    const eventSource = new EventSource("/events");
    eventSource.addEventListener("counter-update", (event) => {
      applyCounterUpdate(JSON.parse(event.data));
    });
    eventSource.onerror = () => {
      console.error("SSE connection error");
    };
  };

  fetchStatus()
    .catch((error) => {
      console.error("initial status fetch failed", error);
    })
    .finally(() => {
      connectEvents();
    });
})();
