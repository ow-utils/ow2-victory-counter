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

  // 調整ボタン
  async function adjust(outcome: string, delta: number) {
    await fetch('/api/adjust', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outcome, delta }),
    });
  }

  // 初期化ボタン
  async function reset() {
    if (confirm('本当にリセットしますか？')) {
      await fetch('/api/initialize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ victories: 0, defeats: 0, draws: 0 }),
      });
    }
  }
</script>

<main>
  <h1>Victory Counter 管理画面</h1>

  <div class="counter-grid">
    <div class="counter-item victory">
      <div class="label">Victory</div>
      <div class="value">{victories ? Math.floor($victories) : 0}</div>
      <div class="controls">
        <button on:click={() => adjust('victory', 1)}>+</button>
        <button on:click={() => adjust('victory', -1)}>-</button>
      </div>
    </div>

    <div class="counter-item defeat">
      <div class="label">Defeat</div>
      <div class="value">{defeats ? Math.floor($defeats) : 0}</div>
      <div class="controls">
        <button on:click={() => adjust('defeat', 1)}>+</button>
        <button on:click={() => adjust('defeat', -1)}>-</button>
      </div>
    </div>
  </div>

  <div class="last-update">
    {formattedLastUpdate()}
  </div>

  <div class="actions">
    <button class="reset-btn" on:click={reset}>リセット</button>
  </div>
</main>

<style>
  main {
    max-width: 800px;
    margin: 0 auto;
    padding: 40px 20px;
    font-family: 'Arial', sans-serif;
  }

  h1 {
    text-align: center;
    color: #333;
    margin-bottom: 40px;
  }

  .counter-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-bottom: 20px;
  }

  .counter-item {
    text-align: center;
    padding: 20px;
    border-radius: 8px;
    background: #f5f5f5;
  }

  .victory {
    border-left: 4px solid #4caf50;
  }

  .defeat {
    border-left: 4px solid #f44336;
  }

  .label {
    font-size: 18px;
    color: #666;
    margin-bottom: 10px;
  }

  .value {
    font-size: 48px;
    font-weight: bold;
    margin: 10px 0;
    color: #333;
  }

  .controls {
    display: flex;
    gap: 10px;
    justify-content: center;
    margin-top: 10px;
  }

  button {
    padding: 8px 20px;
    font-size: 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    background: #2196f3;
    color: white;
    transition: background 0.2s;
  }

  button:hover {
    background: #1976d2;
  }

  .last-update {
    text-align: center;
    font-size: 16px;
    color: #666;
    margin: 20px 0;
    padding: 10px;
    background: #f9f9f9;
    border-radius: 4px;
  }

  .actions {
    text-align: center;
    margin-top: 40px;
  }

  .reset-btn {
    background: #f44336;
  }

  .reset-btn:hover {
    background: #d32f2f;
  }
</style>
