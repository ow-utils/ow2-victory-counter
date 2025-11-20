mod capture;
mod config;
mod predictor;
mod server;
mod state;

use capture::OBSCapture;
use chrono::Local;
use clap::Parser;
use config::Config;
use predictor::VictoryPredictor;
use server::{app, AppState};
use state::StateManager;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tracing::{debug, error, info, warn};
use tracing_subscriber::EnvFilter;

/// Overwatch 2 Victory Counter - Rust implementation
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Path to config file
    #[arg(short, long, default_value = "config.toml")]
    config: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // ログ初期化（環境変数 RUST_LOG で制御可能、デフォルトは info）
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("info"))
        )
        .init();

    info!("Starting ow2-victory-detector...");

    // コマンドライン引数パース
    let args = Args::parse();

    // 設定ファイル読み込み
    info!("Loading config from: {}", args.config);
    let config = Config::from_file(&args.config)?;
    debug!("Config loaded: {:?}", config);

    // OBSCapture初期化
    info!(
        "Connecting to OBS WebSocket at {}:{}...",
        config.obs.host, config.obs.port
    );
    let obs_capture = OBSCapture::new(
        &config.obs.host,
        config.obs.port,
        config.obs.password.as_deref(),
        config.obs.source_name.clone(),
    )
    .await?;
    info!("OBS WebSocket connected successfully");

    // VictoryPredictor初期化
    info!("Loading ONNX model...");
    let predictor = VictoryPredictor::new(
        config.model.model_path.to_str().unwrap(),
        config.model.label_map_path.to_str().unwrap(),
    )?;
    info!("ONNX model loaded successfully");

    // StateManager初期化
    let state_manager = Arc::new(Mutex::new(StateManager::new(
        config.state.cooldown_seconds,
        config.state.required_consecutive,
    )));

    // AppState作成
    let app_state = AppState {
        state_manager: state_manager.clone(),
    };

    // 検知ループをバックグラウンドで起動
    let detection_task = {
        let state_manager = state_manager.clone();
        let config = config.clone();
        tokio::spawn(async move {
            detection_loop(obs_capture, predictor, state_manager, config).await;
        })
    };

    // HTTPサーバー起動
    let server_task = {
        let app = app(app_state);
        let addr = format!("{}:{}", config.server.host, config.server.port);
        info!("HTTP server listening on http://{}", addr);
        info!("  - OBS UI: http://{}/", addr);
        info!("  - Admin UI: http://{}/admin", addr);
        info!("  - SSE endpoint: http://{}/events", addr);

        let listener = tokio::net::TcpListener::bind(&addr).await?;
        tokio::spawn(async move {
            if let Err(e) = axum::serve(listener, app).await {
                error!("Server error: {}", e);
            }
        })
    };

    // 両方のタスクを待機
    tokio::select! {
        _ = detection_task => {
            error!("Detection loop terminated unexpectedly");
        }
        _ = server_task => {
            error!("HTTP server terminated unexpectedly");
        }
    }

    Ok(())
}

/// 検知ループ: 定期的に画像をキャプチャして推論を実行
async fn detection_loop(
    obs_capture: OBSCapture,
    mut predictor: VictoryPredictor,
    state_manager: Arc<Mutex<StateManager>>,
    config: Config,
) {
    let interval = Duration::from_millis(config.detection.interval_ms);
    let crop_rect = config.crop_rect_tuple();

    // スクリーンショット保存ディレクトリの作成
    if config.screenshot.enabled {
        if let Err(e) = tokio::fs::create_dir_all(&config.screenshot.save_dir).await {
            warn!(
                "Failed to create screenshot directory: {}. Screenshot saving disabled.",
                e
            );
        } else {
            info!(
                "Screenshot saving enabled: {}",
                config.screenshot.save_dir.display()
            );
        }
    }

    info!(
        "Starting detection loop (interval: {}ms, crop: {:?})",
        config.detection.interval_ms, crop_rect
    );

    loop {
        // 1. 画像キャプチャ
        let image = match obs_capture.capture().await {
            Ok(img) => img,
            Err(e) => {
                warn!("Failed to capture image: {}", e);
                tokio::time::sleep(interval).await;
                continue;
            }
        };

        // 2. 前処理（クロップ）
        let processed_image = match obs_capture.preprocess(image.clone(), crop_rect) {
            Ok(img) => img,
            Err(e) => {
                warn!("Failed to preprocess image: {}", e);
                tokio::time::sleep(interval).await;
                continue;
            }
        };

        // 3. 推論
        let detection = match predictor.predict(&processed_image) {
            Ok(det) => det,
            Err(e) => {
                warn!("Failed to predict: {}", e);
                tokio::time::sleep(interval).await;
                continue;
            }
        };

        // 全クラスの確率を整形
        let probs_str = detection
            .probabilities
            .iter()
            .map(|(label, prob)| format!("{}={:.2}", label, prob))
            .collect::<Vec<_>>()
            .join(", ");

        debug!(
            "Prediction: [{}] -> outcome={} (confidence={:.2})",
            probs_str, detection.outcome, detection.confidence
        );

        // 4. StateManagerに記録
        let mut manager = state_manager.lock().await;
        let result = manager.record_detection(&detection.outcome);
        drop(manager);

        // 5. スクリーンショット保存（設定で有効 + 最初の検知 + victory/defeat のみ）
        if config.screenshot.enabled
            && result.is_first_detection
            && matches!(detection.outcome.as_str(), "victory" | "defeat")
        {
            let timestamp = Local::now().format("%Y%m%d-%H%M%S-%3f").to_string();
            let filename = format!("{}-{}-first.png", timestamp, detection.predicted_class);
            let filepath = config.screenshot.save_dir.join(&filename);

            // 元画像（前処理前）を保存
            if let Err(e) = image.save(&filepath) {
                warn!("Failed to save screenshot: {}", e);
            } else {
                info!("スクリーンショット保存: {}", filename);
            }
        }

        if result.event_triggered {
            info!(
                "Event triggered: {} (confidence: {:.2})",
                detection.outcome, detection.confidence
            );
        }

        // 6. 次のループまで待機
        tokio::time::sleep(interval).await;
    }
}
