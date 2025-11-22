mod capture;
mod config;
mod predictor;
mod server;
mod state;

use capture::OBSCapture;
use chrono::Local;
use clap::{Parser, Subcommand};
use config::Config;
use predictor::VictoryPredictor;
use server::{app, AppState};
use state::StateManager;
use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::Mutex;
use tracing::{debug, error, info, warn};
use tracing_subscriber::EnvFilter;

/// Overwatch 2 Victory Counter - Rust implementation
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Run as server mode (default)
    Server {
        /// Path to config file
        #[arg(short, long, default_value = "config.toml")]
        config: String,
    },
    /// Run inference on a single image
    Predict {
        /// Path to input image
        #[arg(short, long)]
        image: PathBuf,
        /// Path to config file
        #[arg(short, long, default_value = "config.toml")]
        config: PathBuf,
        /// Output JSON file path (optional, prints to stdout if not specified)
        #[arg(short, long)]
        output: Option<PathBuf>,
        /// Skip cropping
        #[arg(long)]
        no_crop: bool,
    },
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

    // コマンドライン引数パース
    let args = Args::parse();

    // サブコマンドに応じて実行モードを切り替え
    match args.command {
        Some(Commands::Server { config }) => {
            run_server(config).await
        }
        Some(Commands::Predict {
            image,
            config: config_path,
            output,
            no_crop,
        }) => {
            run_predict(image, config_path, output, no_crop).await
        }
        None => {
            // サブコマンドが指定されていない場合はデフォルトでサーバーモード
            run_server("config.toml".to_string()).await
        }
    }
}

/// サーバーモード: OBSから画像をキャプチャして推論を実行
async fn run_server(config_path: String) -> Result<(), Box<dyn std::error::Error>> {
    info!("Starting ow2-victory-detector...");

    // 設定ファイル読み込み
    info!("Loading config from: {}", config_path);
    let config = Config::from_file(&config_path)?;
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
        config.model.class_map.clone(),
        config.preprocessing.resize_width,
        config.preprocessing.resize_height,
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

    // デバッグディレクトリの作成
    if config.debug.enabled {
        if let Err(e) = tokio::fs::create_dir_all(&config.debug.save_dir).await {
            warn!(
                "Failed to create debug directory: {}. Debug mode disabled.",
                e
            );
        } else {
            info!("Debug mode enabled: {}", config.debug.save_dir.display());
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
        let processed_image = match OBSCapture::preprocess(image.clone(), crop_rect) {
            Ok(img) => img,
            Err(e) => {
                warn!("Failed to preprocess image: {}", e);
                tokio::time::sleep(interval).await;
                continue;
            }
        };

        // デバッグ: クロップ後の画像を保存
        if config.debug.enabled && config.debug.save_cropped {
            let timestamp = Local::now().format("%Y%m%d-%H%M%S-%3f");
            let filename = format!("cropped-{}.png", timestamp);
            let filepath = config.debug.save_dir.join(&filename);
            if let Err(e) = processed_image.save(&filepath) {
                warn!("Failed to save cropped image: {}", e);
            }
        }

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

        // デバッグ: 推論結果を保存
        if config.debug.enabled && config.debug.save_results {
            let timestamp = Local::now().format("%Y%m%d-%H%M%S-%3f");
            let result_json = serde_json::json!({
                "timestamp": timestamp.to_string(),
                "outcome": detection.outcome,
                "confidence": detection.confidence,
                "predicted_class": detection.predicted_class,
                "probabilities": detection.probabilities,
            });
            let filename = format!("result-{}.json", timestamp);
            let filepath = config.debug.save_dir.join(&filename);
            if let Err(e) = tokio::fs::write(&filepath, serde_json::to_string_pretty(&result_json).unwrap()).await {
                warn!("Failed to save result: {}", e);
            }
        }

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

/// 画像推論モード: 単一の画像に対して推論を実行
async fn run_predict(
    image_path: PathBuf,
    config_path: PathBuf,
    output_path: Option<PathBuf>,
    no_crop: bool,
) -> Result<(), Box<dyn std::error::Error>> {
    info!("Running prediction on single image: {:?}", image_path);

    // 1. 画像読み込み
    if !image_path.exists() {
        error!("Image not found: {:?}", image_path);
        std::process::exit(1);
    }

    let image = image::open(&image_path)
        .map_err(|e| format!("Failed to load image: {}", e))?;

    info!("Image loaded: {}x{} (WxH)", image.width(), image.height());

    // 2. コンフィグ読み込み（サーバーと同じ設定を使用）
    info!("Loading config for predict from: {:?}", config_path);
    let config = Config::from_file(config_path.to_str().unwrap())?;

    // 3. 前処理（クロップ）
    let processed_image = if no_crop {
        info!("Skipping crop");
        image
    } else {
        let crop_rect = config.crop_rect_tuple();
        info!("Cropping with rect: {:?}", crop_rect);

        let (x, y, width, height) = crop_rect;

        // クロップパラメータの検証
        if x + width > image.width() || y + height > image.height() {
            warn!(
                "Crop region exceeds image dimensions, using full image instead"
            );
            image
        } else {
            image.crop_imm(x, y, width, height)
        }
    };

    info!(
        "Processed image size: {}x{}",
        processed_image.width(),
        processed_image.height()
    );

    // 4. VictoryPredictor初期化
    info!("Loading ONNX model from: {:?}", config.model.model_path);
    let (target_width, target_height, class_map) = (
        config.preprocessing.resize_width,
        config.preprocessing.resize_height,
        config.model.class_map.clone(),
    );
    let mut predictor = VictoryPredictor::new(
        config.model.model_path.to_str().unwrap(),
        config.model.label_map_path.to_str().unwrap(),
        class_map,
        target_width,
        target_height,
    )?;
    info!("ONNX model loaded successfully");

    // 5. 推論実行
    let detection = predictor.predict(&processed_image)?;

    // 6. 結果を辞書化
    let result = serde_json::json!({
        "image": image_path.to_str().unwrap(),
        "outcome": detection.outcome,
        "confidence": detection.confidence,
        "predicted_class": detection.predicted_class,
        "probabilities": detection.probabilities.iter().map(|(label, prob)| {
            serde_json::json!({
                "class": label,
                "probability": prob,
            })
        }).collect::<Vec<_>>(),
    });

    // 6. 出力
    // 7. 出力
    if let Some(output_path) = output_path {
        tokio::fs::write(
            &output_path,
            serde_json::to_string_pretty(&result)?,
        )
        .await?;
        info!("Result saved to: {:?}", output_path);
    } else {
        println!("{}", serde_json::to_string_pretty(&result)?);
    }

    Ok(())
}
