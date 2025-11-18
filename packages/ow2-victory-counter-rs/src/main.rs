mod capture;
mod predictor;
mod server;
mod state;

use server::{app, AppState};
use state::StateManager;
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::{info, Level};
use tracing_subscriber;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ログ初期化
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    info!("Starting ow2-victory-detector...");

    // StateManager初期化（クールダウン10秒、連続3回検知）
    let state_manager = Arc::new(Mutex::new(StateManager::new(10, 3)));

    // AppState作成
    let app_state = AppState {
        state_manager: state_manager.clone(),
    };

    // HTTPサーバー起動
    let app = app(app_state);
    let addr = "127.0.0.1:3000";
    info!("HTTP server listening on http://{}", addr);
    info!("  - OBS UI: http://{}/", addr);
    info!("  - Admin UI: http://{}/admin", addr);
    info!("  - SSE endpoint: http://{}/events", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
