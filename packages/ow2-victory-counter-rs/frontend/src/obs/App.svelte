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
    background: radial-gradient(circle at 20% 20%, rgba(116, 198, 255, 0.12), transparent 35%),
      radial-gradient(circle at 75% 25%, rgba(255, 188, 143, 0.14), transparent 40%),
      linear-gradient(145deg, #0f1729, #0c1222 45%, #0d111d);
    font-family: 'Plus Jakarta Sans', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    letter-spacing: 0.01em;
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
  }

  .counter-grid {
    --victory-color: #a3ffcb;
    --defeat-color: #ffb3c7;
    --font-size: clamp(52px, 8vw, 92px);
    --gap: clamp(16px, 4vw, 44px);

    display: grid;
    grid-template-columns: repeat(2, minmax(200px, 1fr));
    gap: var(--gap);
    margin-bottom: 28px;
    width: min(1200px, 90vw);
  }

  .counter-item {
    position: relative;
    padding: clamp(20px, 4vw, 36px);
    border-radius: 18px;
    text-align: center;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.04));
    box-shadow:
      0 18px 48px rgba(0, 0, 0, 0.35),
      inset 0 0 24px rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    isolation: isolate;
  }

  .counter-item::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 18px;
    background: radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.12), transparent 45%),
      radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.08), transparent 50%);
    z-index: 0;
    pointer-events: none;
  }

  .counter-item::after {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 18px;
    background: linear-gradient(120deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0));
    z-index: 0;
    mix-blend-mode: screen;
  }

  .counter-content {
    position: relative;
    z-index: 1;
  }

  .victory .value {
    color: var(--victory-color);
    text-shadow:
      0 4px 18px rgba(163, 255, 203, 0.55),
      0 0 32px rgba(163, 255, 203, 0.35);
  }

  .defeat .value {
    color: var(--defeat-color);
    text-shadow:
      0 4px 18px rgba(255, 179, 199, 0.55),
      0 0 32px rgba(255, 179, 199, 0.35);
  }

  .label {
    font-size: clamp(18px, 3vw, 28px);
    opacity: 0.95;
    text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.7);
    letter-spacing: 0.12em;
    font-weight: 600;
  }

  .value {
    font-size: var(--font-size);
    font-weight: 800;
    display: inline-block;
    will-change: transform, filter;
    letter-spacing: 0.05em;
  }

  .last-update {
    font-size: 16px;
    color: #e7ecff;
    text-shadow: 1px 2px 8px rgba(0, 0, 0, 0.65);
    opacity: 0.95;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    padding: 10px 16px;
    border-radius: 999px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }
</style>
