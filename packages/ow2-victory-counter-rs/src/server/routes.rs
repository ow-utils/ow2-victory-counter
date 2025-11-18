use crate::state::{CounterUpdate, StateManager};
use axum::{
    extract::State,
    http::StatusCode,
    response::{
        sse::{Event, KeepAlive, Sse},
        Html, IntoResponse, Response,
    },
    routing::{get, post},
    Json, Router,
};
use serde::Deserialize;
use std::convert::Infallible;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tokio_stream::{wrappers::BroadcastStream, StreamExt};

#[derive(Clone)]
pub struct AppState {
    pub state_manager: Arc<Mutex<StateManager>>,
}

pub fn app(state: AppState) -> Router {
    Router::new()
        .route("/", get(serve_obs_ui))
        .route("/admin", get(serve_admin_ui))
        .route("/custom.css", get(serve_custom_css))
        .route("/events", get(sse_handler))
        .route("/api/status", get(get_status))
        .route("/api/initialize", post(initialize))
        .route("/api/adjust", post(adjust))
        .with_state(state)
}

async fn serve_obs_ui() -> Html<String> {
    // 開発モード: Viteプロキシ経由、本番モード: バイナリー組み込み
    #[cfg(debug_assertions)]
    {
        Html(
            r#"<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OBS Victory Counter</title>
</head>
<body>
  <div id="app"></div>
  <script type="module">
    // 開発モードではVite dev server (localhost:5173) へリダイレクト
    window.location.href = 'http://localhost:5173/obs.html';
  </script>
</body>
</html>"#
                .to_string(),
        )
    }

    #[cfg(not(debug_assertions))]
    {
        // 本番モード: フロントエンドビルド成果物を組み込み
        Html(include_str!("../../frontend/dist/obs.html").to_string())
    }
}

async fn serve_admin_ui() -> Html<String> {
    // 開発モード: Viteプロキシ経由、本番モード: バイナリー組み込み
    #[cfg(debug_assertions)]
    {
        Html(
            r#"<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Victory Counter 管理画面</title>
</head>
<body>
  <div id="app"></div>
  <script type="module">
    // 開発モードではVite dev server (localhost:5173) へリダイレクト
    window.location.href = 'http://localhost:5173/admin.html';
  </script>
</body>
</html>"#
                .to_string(),
        )
    }

    #[cfg(not(debug_assertions))]
    {
        // 本番モード: フロントエンドビルド成果物を組み込み
        Html(include_str!("../../frontend/dist/admin.html").to_string())
    }
}

async fn serve_custom_css() -> Result<Response, StatusCode> {
    // 外部ファイル優先（カスタマイズ用）
    if let Ok(css) = tokio::fs::read_to_string("templates/custom.css").await {
        return Ok(Response::builder()
            .header("Content-Type", "text/css")
            .body(css.into())
            .unwrap());
    }

    // デフォルトは空CSS
    Ok(Response::builder()
        .header("Content-Type", "text/css")
        .body("".into())
        .unwrap())
}

async fn sse_handler(
    State(state): State<AppState>,
) -> Sse<impl tokio_stream::Stream<Item = Result<Event, Infallible>>> {
    let manager = state.state_manager.lock().await;
    let rx = manager.subscribe();
    drop(manager);

    let stream = BroadcastStream::new(rx).map(|result| {
        result
            .map(|update| {
                Event::default()
                    .event("counter-update")
                    .json_data(&update)
                    .unwrap()
            })
            .map_err(|_| Infallible)
    });

    Sse::new(stream).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(15))
            .text("keep-alive"),
    )
}

async fn get_status(State(state): State<AppState>) -> Json<CounterUpdate> {
    let manager = state.state_manager.lock().await;
    Json(manager.summary())
}

#[derive(Deserialize)]
struct InitializeRequest {
    victories: u32,
    defeats: u32,
    draws: u32,
}

async fn initialize(
    State(state): State<AppState>,
    Json(data): Json<InitializeRequest>,
) -> Json<CounterUpdate> {
    let mut manager = state.state_manager.lock().await;
    manager.initialize(data.victories, data.defeats, data.draws);
    Json(manager.summary())
}

#[derive(Deserialize)]
struct AdjustRequest {
    outcome: String,
    delta: i32,
}

async fn adjust(
    State(state): State<AppState>,
    Json(data): Json<AdjustRequest>,
) -> Json<CounterUpdate> {
    let mut manager = state.state_manager.lock().await;
    manager.adjust(&data.outcome, data.delta);
    Json(manager.summary())
}
