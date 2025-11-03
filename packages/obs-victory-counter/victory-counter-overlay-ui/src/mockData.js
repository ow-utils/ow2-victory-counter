const baseTime = new Date("2025-01-01T12:00:00Z").getTime();

const minutes = (offset) => baseTime + offset * 60_000;

export const mockTimeline = [
  {
    type: "result",
    value: "victory",
    delta: 1,
    timestamp: new Date(minutes(0)).toISOString(),
    confidence: 0.92,
  },
  {
    type: "result",
    value: "defeat",
    delta: 1,
    timestamp: new Date(minutes(10)).toISOString(),
    confidence: 0.75,
  },
  {
    type: "result",
    value: "victory",
    delta: 1,
    timestamp: new Date(minutes(20)).toISOString(),
    confidence: 0.88,
  },
  {
    type: "adjustment",
    value: "victory",
    delta: 1,
    timestamp: new Date(minutes(22)).toISOString(),
    note: "Manual correction",
  },
  {
    type: "result",
    value: "victory",
    delta: 1,
    timestamp: new Date(minutes(35)).toISOString(),
    confidence: 0.82,
  },
  {
    type: "result",
    value: "defeat",
    delta: 1,
    timestamp: new Date(minutes(45)).toISOString(),
    confidence: 0.7,
  },
  {
    type: "result",
    value: "draw",
    delta: 1,
    timestamp: new Date(minutes(50)).toISOString(),
    confidence: 0.95,
  },
  {
    type: "result",
    value: "victory",
    delta: 1,
    timestamp: new Date(minutes(55)).toISOString(),
    confidence: 0.9,
  },
  {
    type: "adjustment",
    value: "defeat",
    delta: 1,
    timestamp: new Date(minutes(57)).toISOString(),
    note: "Opponent requested review",
  },
];

export const summarizeEvents = (events) =>
  events.reduce(
    (acc, event) => {
      if (event.value === "victory") {
        acc.victories += event.delta;
      } else if (event.value === "defeat") {
        acc.defeats += event.delta;
      } else if (event.value === "draw") {
        acc.draws += event.delta;
      }
      acc.total = acc.victories + acc.defeats + acc.draws;
      return acc;
    },
    { victories: 0, defeats: 0, draws: 0, total: 0 },
  );
