use crate::state::{CounterUpdate, StateManager};
use axum::{
    Json, Router,
    extract::State,
    http::StatusCode,
    response::{
        Html, Response,
        sse::{Event, KeepAlive, Sse},
    },
    routing::{get, post},
};
use serde::Deserialize;
use std::convert::Infallible;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tokio_stream::{StreamExt, wrappers::BroadcastStream};
#[cfg(not(debug_assertions))]
use tower_http::services::ServeDir;

const DEFAULT_COUNTER_HTML: &str = include_str!("../../templates/counter.html");
const DEFAULT_COUNTER_CSS: &str = include_str!("../../templates/counter.css");
const DEFAULT_COUNTER_JS: &str = include_str!("../../templates/counter.js");

#[derive(Clone)]
pub struct AppState {
    pub state_manager: Arc<Mutex<StateManager>>,
}

pub fn app(state: AppState) -> Router {
    // 本番モード: frontend/dist/assets から静的ファイルを提供
    #[cfg(not(debug_assertions))]
    let router = Router::new()
        .route("/", get(serve_obs_ui))
        .route("/admin", get(serve_admin_ui))
        .route("/counter.css", get(serve_counter_css))
        .route("/counter.js", get(serve_counter_js))
        .route("/events", get(sse_handler))
        .route("/api/status", get(get_status))
        .route("/api/initialize", post(initialize))
        .route("/api/adjust", post(adjust))
        .nest_service("/assets", ServeDir::new("frontend/dist/assets"))
        .fallback_service(ServeDir::new("frontend/dist"))
        .with_state(state);

    // 開発モード: Vite dev server が静的ファイルを提供
    #[cfg(debug_assertions)]
    let router = Router::new()
        .route("/", get(serve_obs_ui))
        .route("/admin", get(serve_admin_ui))
        .route("/counter.css", get(serve_counter_css))
        .route("/counter.js", get(serve_counter_js))
        .route("/events", get(sse_handler))
        .route("/api/status", get(get_status))
        .route("/api/initialize", post(initialize))
        .route("/api/adjust", post(adjust))
        .with_state(state);

    router
}

async fn serve_obs_ui() -> Html<String> {
    let body = read_customizable_file("assets/counter.html", DEFAULT_COUNTER_HTML).await;
    Html(render_obs_document(&body))
}

async fn serve_admin_ui() -> Html<String> {
    // 開発モード: Viteプロキシ経由、本番モード: ファイルシステムから配信
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
        let html = std::fs::read_to_string("frontend/dist/admin.html")
            .unwrap_or_else(|_| "<h1>admin.html not found</h1>".to_string());
        Html(html)
    }
}

async fn serve_counter_css() -> Result<Response, StatusCode> {
    let css = read_customizable_file("assets/counter.css", DEFAULT_COUNTER_CSS).await;
    Ok(Response::builder()
        .header("Content-Type", "text/css; charset=utf-8")
        .body(css.into())
        .unwrap())
}

async fn serve_counter_js() -> Result<Response, StatusCode> {
    let js = read_customizable_file("assets/counter.js", DEFAULT_COUNTER_JS).await;
    Ok(Response::builder()
        .header("Content-Type", "application/javascript; charset=utf-8")
        .body(js.into())
        .unwrap())
}

async fn read_customizable_file(path: &str, fallback: &str) -> String {
    tokio::fs::read_to_string(path)
        .await
        .unwrap_or_else(|_| fallback.to_string())
}

fn render_obs_document(body: &str) -> String {
    format!(
        r#"<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OW2 Victory Counter</title>
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="/counter.css" />
</head>
<body>
  {body}
  <script src="/counter.js"></script>
</body>
</html>
"#,
        body = body
    )
}

async fn sse_handler(
    State(state): State<AppState>,
) -> Sse<impl tokio_stream::Stream<Item = Result<Event, Infallible>>> {
    let manager = state.state_manager.lock().await;
    let current_state = manager.summary();
    let rx = manager.subscribe();
    drop(manager);

    // 接続時に現在の状態を即座に送信
    let initial = tokio_stream::once(Ok(Event::default()
        .event("counter-update")
        .json_data(&current_state)
        .unwrap()));

    // その後、broadcast streamで更新を受信
    let updates = BroadcastStream::new(rx).filter_map(|result| match result {
        Ok(update) => Some(Ok(Event::default()
            .event("counter-update")
            .json_data(&update)
            .unwrap())),
        Err(_) => None,
    });

    // 初期データ + リアルタイム更新
    let stream = initial.chain(updates);

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rendered_obs_document_uses_counter_css_and_bindings() {
        let html = render_obs_document(r#"<div data-counter="victories">0</div>"#);

        assert!(html.contains(r#"<link rel="stylesheet" href="/counter.css" />"#));
        assert!(html.contains("fonts.googleapis.com"));
        assert!(html.contains("Bebas+Neue"));
        assert!(html.contains(r#"<script src="/counter.js"></script>"#));
        assert!(html.contains(r#"data-counter="victories""#));
    }

    #[test]
    fn bundled_defaults_expose_template_bindings() {
        assert!(DEFAULT_COUNTER_HTML.contains(r#"data-counter="victories""#));
        assert!(DEFAULT_COUNTER_HTML.contains(r#"data-meta="winrate""#));
        assert!(DEFAULT_COUNTER_HTML.contains(r#"data-style="winrate-width""#));
        assert!(DEFAULT_COUNTER_CSS.contains(".counter-container"));
        assert!(DEFAULT_COUNTER_JS.contains(r#"new EventSource("/events")"#));
        assert!(DEFAULT_COUNTER_JS.contains(r#"fetch("/api/status")"#));
    }
}
