(() => {
  const outcomeLabels = {
    victory: "Victory",
    defeat: "Defeat",
    draw: "Draw",
  };
  const previousCounters = new Map();

  const playBump = (element) => {
    if (!element || typeof element.animate !== "function") {
      return;
    }
    element.animate(
      [
        {
          transform: "scale(1)",
          filter: "drop-shadow(0 0 0 rgba(255,255,255,0.2))",
        },
        {
          transform: "scale(1.2)",
          filter: "drop-shadow(0 0 20px rgba(255,255,255,0.5))",
        },
        {
          transform: "scale(1)",
          filter: "drop-shadow(0 0 0 rgba(255,255,255,0.2))",
        },
      ],
      { duration: 520, easing: "ease" },
    );
  };

  const setText = (attrName, key, value) => {
    document.querySelectorAll(`[${attrName}="${key}"]`).forEach((element) => {
      element.textContent = value;
    });
  };

  const setCounterText = (key, value) => {
    const previousValue = previousCounters.get(key);
    document.querySelectorAll(`[data-counter="${key}"]`).forEach((element) => {
      element.textContent = value;
      if (previousValue !== undefined && previousValue !== value) {
        playBump(element);
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

    setCounterText("victories", String(victories));
    setCounterText("defeats", String(defeats));
    setCounterText("draws", String(draws));
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
