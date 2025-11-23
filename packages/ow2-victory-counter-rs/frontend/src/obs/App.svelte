<script lang="ts">
  import { onMount } from 'svelte';

  // Svelte 5 ルーン方式
  let victories = $state(0);
  let defeats = $state(0);
  let lastOutcome = $state<string | null>(null);
  let lastUpdated = $state<number | null>(null);
  let prevVictories: number | null = null;
  let prevDefeats: number | null = null;
  let prevUpdated: number | null = null;
  let victoryValueEl: HTMLDivElement | null = null;
  let defeatValueEl: HTMLDivElement | null = null;
  let lastUpdateEl: HTMLDivElement | null = null;

  // Web Animations API で確実に再生させる
  const playBump = (el: HTMLElement | null) => {
    if (!el) return;
    el.animate(
      [
        { transform: 'scale(1)', filter: 'drop-shadow(0 0 0 rgba(255,255,255,0.2))' },
        { transform: 'scale(1.2)', filter: 'drop-shadow(0 0 20px rgba(255,255,255,0.5))' },
        { transform: 'scale(1)', filter: 'drop-shadow(0 0 0 rgba(255,255,255,0.2))' },
      ],
      { duration: 520, easing: 'ease' }
    );
  };

  const playFlash = (el: HTMLElement | null) => {
    if (!el) return;
    el.animate(
      [
        { opacity: 0.4 },
        { opacity: 1 },
        { opacity: 0.9 },
      ],
      { duration: 600, easing: 'ease' }
    );
  };

  // 最終更新情報のフォーマット
  let formattedLastUpdate = $derived(() => {
    if (!lastUpdated || !lastOutcome) return '更新なし';
    const date = new Date(lastUpdated * 1000);
    const formatted = date.toLocaleString('ja-JP');
    const outcomeText = lastOutcome === 'victory' ? 'Victory' : 'Defeat';
    return `最終更新: ${formatted} - ${outcomeText}`;
  });

  // onMount で SSE接続を確立
  onMount(() => {
    // SSE接続
    const eventSource = new EventSource('/events');

    eventSource.addEventListener('counter-update', (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      victories = data.victories;
      defeats = data.defeats;
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

  // 値の変化を監視してアニメーションを走らせる
  $effect(() => {
    if (prevVictories !== null && victories !== prevVictories) {
      playBump(victoryValueEl);
    }
    prevVictories = victories;
  });

  $effect(() => {
    if (prevDefeats !== null && defeats !== prevDefeats) {
      playBump(defeatValueEl);
    }
    prevDefeats = defeats;
  });

  $effect(() => {
    if (prevUpdated !== null && lastUpdated !== prevUpdated) {
      playFlash(lastUpdateEl);
    }
    prevUpdated = lastUpdated;
  });
</script>

<div class="counter-container">
  <div class="counter-grid">
    <div class="counter-item victory">
      <div class="label">Victory</div>
      <div class="value" bind:this={victoryValueEl}>{victories}</div>
    </div>

    <div class="counter-item defeat">
      <div class="label">Defeat</div>
      <div class="value" bind:this={defeatValueEl}>{defeats}</div>
    </div>
  </div>

  <div class="last-update" bind:this={lastUpdateEl}>
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
    display: inline-block;
    will-change: transform, filter;
  }

  .last-update {
    font-size: 18px;
    color: #ffffff;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9);
    opacity: 0.9;
  }
</style>
