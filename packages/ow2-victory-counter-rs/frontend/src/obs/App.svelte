<script lang="ts">
  import { onMount } from 'svelte';
  import { tweened } from 'svelte/motion';
  import { cubicOut } from 'svelte/easing';
  import type { Tweened } from 'svelte/motion';

  // Svelte 5 ルーン方式
  let victories: Tweened<number>;
  let defeats: Tweened<number>;
  let lastOutcome = $state<string | null>(null);
  let lastUpdated = $state<number | null>(null);

  // 最終更新情報のフォーマット
  let formattedLastUpdate = $derived(() => {
    if (!lastUpdated || !lastOutcome) return '更新なし';
    const date = new Date(lastUpdated * 1000);
    const formatted = date.toLocaleString('ja-JP');
    const outcomeText = lastOutcome === 'victory' ? 'Victory' : 'Defeat';
    return `最終更新: ${formatted} - ${outcomeText}`;
  });

  // onMount で tweened を初期化し、SSE接続を確立
  onMount(() => {
    victories = tweened(0, { duration: 1000, easing: cubicOut });
    defeats = tweened(0, { duration: 1000, easing: cubicOut });

    // SSE接続
    const eventSource = new EventSource('/events');

    eventSource.addEventListener('counter-update', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      victories.set(data.victories);
      defeats.set(data.defeats);
      lastOutcome = data.last_outcome;
      lastUpdated = data.timestamp;
    });

    eventSource.onerror = () => {
      console.error('SSE connection error, reconnecting...');
    };

    // クリーンアップ
    return () => {
      eventSource.close();
    };
  });
</script>

<div class="counter-container">
  <div class="counter-grid">
    <div class="counter-item victory">
      <div class="label">Victory</div>
      <div class="value">{victories ? Math.floor($victories) : 0}</div>
    </div>

    <div class="counter-item defeat">
      <div class="label">Defeat</div>
      <div class="value">{defeats ? Math.floor($defeats) : 0}</div>
    </div>
  </div>

  <div class="last-update">
    {formattedLastUpdate()}
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: transparent;
    font-family: 'Arial', sans-serif;
  }

  .counter-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 40px;
  }

  .counter-grid {
    --victory-color: #4caf50;
    --defeat-color: #f44336;
    --font-size: 64px;
    --gap: 40px;

    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--gap);
    margin-bottom: 20px;
  }

  .counter-item {
    text-align: center;
  }

  .victory {
    color: var(--victory-color);
  }

  .defeat {
    color: var(--defeat-color);
  }

  .label {
    font-size: calc(var(--font-size) * 0.5);
    opacity: 0.8;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9);
  }

  .value {
    font-size: var(--font-size);
    font-weight: bold;
    text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.9);
  }

  .last-update {
    font-size: 18px;
    color: #ffffff;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9);
    opacity: 0.9;
  }
</style>
