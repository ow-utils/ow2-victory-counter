type StateResponse = {
  victories: number;
  defeats: number;
  total: number;
};

const root = document.getElementById("app");

const renderState = (state: StateResponse) => {
  if (!root) {
    // eslint-disable-next-line no-console
    console.warn("Root element #app が見つかりません。");
    return;
  }

  root.innerHTML = `
    <div>
      <p>Victory: ${state.victories}</p>
      <p>Defeat: ${state.defeats}</p>
      <p>Total: ${state.total}</p>
    </div>
  `;
};

const placeholderState: StateResponse = {
  victories: 0,
  defeats: 0,
  total: 0,
};

renderState(placeholderState);
