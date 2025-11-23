<script lang="ts">
  import { onMount } from 'svelte';

  // Svelte 5 ルーン方式
  let victories = $state(0);
  let defeats = $state(0);
  let lastOutcome = $state<string | null>(null);
  let lastUpdated = $state<number | null>(null);
  let victoryValueEl: HTMLDivElement | null = null;
  let defeatValueEl: HTMLDivElement | null = null;
  let lastUpdateEl: HTMLDivElement | null = null;

  // 更新時のワンショットアニメーション用
  const triggerPulse = (el: HTMLElement | null, className: string) => {
    if (!el) return;
    el.classList.remove(className);
    // reflow で強制的にアニメーションをリセット
    void el.offsetWidth;
    el.classList.add(className);
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
      const victoryChanged = data.victories !== victories;
      const defeatChanged = data.defeats !== defeats;

      victories = data.victories;
      defeats = data.defeats;
      lastOutcome = data.last_outcome;
      lastUpdated = data.timestamp;

      if (victoryChanged) {
        triggerPulse(victoryValueEl, 'bump');
      }
      if (defeatChanged) {
        triggerPulse(defeatValueEl, 'bump');
      }
      triggerPulse(lastUpdateEl, 'flash');
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
  }
  .value.bump {
    animation: bump 320ms ease;
  }

  @keyframes bump {
    0% {
      transform: scale(1);
      filter: drop-shadow(0 0 0 rgba(255, 255, 255, 0.2));
    }
    35% {
      transform: scale(1.12);
      filter: drop-shadow(0 0 14px rgba(255, 255, 255, 0.35));
    }
    100% {
      transform: scale(1);
      filter: drop-shadow(0 0 0 rgba(255, 255, 255, 0.2));
    }
  }

  .last-update {
    font-size: 18px;
    color: #ffffff;
    text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9);
    opacity: 0.9;
  }
  .last-update.flash {
    animation: flash 600ms ease;
  }

  @keyframes flash {
    0% {
      opacity: 0.4;
    }
    40% {
      opacity: 1;
    }
    100% {
      opacity: 0.9;
    }
  }
</style>
