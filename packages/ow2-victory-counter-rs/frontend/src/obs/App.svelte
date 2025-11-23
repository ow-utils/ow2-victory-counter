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
    font-family: 'Bebas Neue', 'Arial Black', 'Arial', sans-serif;
    letter-spacing: 0.02em;
  }

  .counter-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 48px;
    box-sizing: border-box;
    color: #f5f8ff;
    background: transparent;
  }

  .counter-grid {
    --victory-color: #7bf36b;
    --defeat-color: #ff5f8d;
    --font-size: clamp(52px, 8vw, 96px);
    --gap: clamp(16px, 4vw, 48px);

    display: grid;
    grid-template-columns: repeat(2, minmax(200px, 320px));
    justify-content: center;
    gap: var(--gap);
    margin-bottom: 28px;
    width: min(900px, 92vw);
  }

  .counter-item {
    position: relative;
    text-align: center;
    padding: clamp(14px, 3vw, 24px);
    border-radius: 16px;
    background: rgba(12, 14, 28, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow:
      0 12px 38px rgba(0, 0, 0, 0.4),
      inset 0 0 18px rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    overflow: hidden;
  }

  .counter-item::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 16px;
    background: radial-gradient(circle at 25% 20%, rgba(255, 255, 255, 0.12), transparent 45%),
      radial-gradient(circle at 80% 15%, rgba(255, 255, 255, 0.08), transparent 50%);
    pointer-events: none;
    mix-blend-mode: screen;
  }

  .victory .value {
    color: var(--victory-color);
    text-shadow:
      0 0 12px rgba(123, 243, 107, 0.55),
      0 0 28px rgba(123, 243, 107, 0.35);
  }

  .defeat .value {
    color: var(--defeat-color);
    text-shadow:
      0 0 12px rgba(255, 95, 141, 0.55),
      0 0 28px rgba(255, 95, 141, 0.35);
  }

  .label {
    font-size: clamp(18px, 3vw, 28px);
    opacity: 0.95;
    text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.7);
    letter-spacing: 0.08em;
  }

  .value {
    font-size: var(--font-size);
    font-weight: 800;
    display: inline-block;
    will-change: transform, filter;
    letter-spacing: 0.05em;
  }

  .last-update {
    font-size: 17px;
    color: #d6dcff;
    text-shadow: 2px 2px 6px rgba(0, 0, 0, 0.8);
    opacity: 0.9;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    padding: 10px 16px;
    border-radius: 999px;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }
</style>
