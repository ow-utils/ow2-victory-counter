use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    /// OBS接続設定
    pub obs: ObsConfig,
    /// 推論モデル設定
    pub model: ModelConfig,
    /// 画像前処理設定
    pub preprocessing: PreprocessingConfig,
    /// 状態管理設定
    pub state: StateConfig,
    /// HTTPサーバー設定
    pub server: ServerConfig,
    /// 検知ループ設定
    pub detection: DetectionConfig,
    /// スクリーンショット保存設定
    pub screenshot: ScreenshotConfig,
    /// デバッグ設定
    pub debug: DebugConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObsConfig {
    /// OBS WebSocket ホスト
    #[serde(default = "default_obs_host")]
    pub host: String,
    /// OBS WebSocket ポート
    #[serde(default = "default_obs_port")]
    pub port: u16,
    /// OBS WebSocket パスワード (オプション)
    pub password: Option<String>,
    /// キャプチャするOBSソース名
    pub source_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelConfig {
    /// ONNXモデルファイルのパス
    pub model_path: PathBuf,
    /// ラベルマップJSONファイルのパス
    pub label_map_path: PathBuf,
    /// クラス名→outcome のマッピング（未指定時はフォールバックロジックを使用）
    #[serde(default = "default_class_map")]
    pub class_map: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PreprocessingConfig {
    /// クロップ領域 [x, y, width, height]
    pub crop_rect: [u32; 4],
    /// 推論モデルに入力するリサイズ後の幅
    #[serde(default = "default_resize_width")]
    pub resize_width: u32,
    /// 推論モデルに入力するリサイズ後の高さ
    #[serde(default = "default_resize_height")]
    pub resize_height: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateConfig {
    /// クールダウン秒数
    #[serde(default = "default_cooldown_seconds")]
    pub cooldown_seconds: u64,
    /// 連続検知必要回数
    #[serde(default = "default_required_consecutive")]
    pub required_consecutive: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    /// HTTPサーバーホスト
    #[serde(default = "default_server_host")]
    pub host: String,
    /// HTTPサーバーポート
    #[serde(default = "default_server_port")]
    pub port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectionConfig {
    /// 検知ループ間隔 (ミリ秒)
    #[serde(default = "default_detection_interval_ms")]
    pub interval_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenshotConfig {
    /// スクリーンショット保存機能を有効にするか
    #[serde(default = "default_screenshot_enabled")]
    pub enabled: bool,
    /// スクリーンショット保存先ディレクトリ
    #[serde(default = "default_screenshot_save_dir")]
    pub save_dir: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DebugConfig {
    /// デバッグ機能を有効にするか
    #[serde(default = "default_debug_enabled")]
    pub enabled: bool,
    /// デバッグ出力先ディレクトリ
    #[serde(default = "default_debug_save_dir")]
    pub save_dir: PathBuf,
    /// クロップ後の画像を保存するか
    #[serde(default = "default_debug_save_cropped")]
    pub save_cropped: bool,
    /// 前処理後の画像を保存するか（未実装）
    #[serde(default = "default_debug_save_preprocessed")]
    pub save_preprocessed: bool,
    /// 推論結果を保存するか
    #[serde(default = "default_debug_save_results")]
    pub save_results: bool,
}

// デフォルト値関数
fn default_obs_host() -> String {
    "localhost".to_string()
}

fn default_obs_port() -> u16 {
    4455
}

fn default_cooldown_seconds() -> u64 {
    10
}

fn default_required_consecutive() -> usize {
    3
}

fn default_server_host() -> String {
    "127.0.0.1".to_string()
}

fn default_server_port() -> u16 {
    3000
}

fn default_detection_interval_ms() -> u64 {
    1000
}

fn default_resize_width() -> u32 {
    512
}

fn default_resize_height() -> u32 {
    283
}

fn default_screenshot_enabled() -> bool {
    false
}

fn default_screenshot_save_dir() -> PathBuf {
    PathBuf::from("screenshots")
}

fn default_debug_enabled() -> bool {
    false
}

fn default_debug_save_dir() -> PathBuf {
    PathBuf::from("debug")
}

fn default_debug_save_cropped() -> bool {
    true
}

fn default_debug_save_preprocessed() -> bool {
    false
}

fn default_debug_save_results() -> bool {
    true
}

fn default_class_map() -> HashMap<String, String> {
    HashMap::new()
}

impl Config {
    /// TOMLファイルから設定を読み込む
    pub fn from_file(path: &str) -> Result<Self, ConfigError> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| ConfigError::FileRead(path.to_string(), e.to_string()))?;

        let config: Config = toml::from_str(&content)
            .map_err(|e| ConfigError::Parse(path.to_string(), e.to_string()))?;

        Ok(config)
    }

    /// デフォルト設定を作成
    #[allow(dead_code)]
    pub fn default_with_required(source_name: String, model_path: PathBuf) -> Self {
        Self {
            obs: ObsConfig {
                host: default_obs_host(),
                port: default_obs_port(),
                password: None,
                source_name,
            },
            model: ModelConfig {
                model_path: model_path.clone(),
                label_map_path: model_path.with_extension("label_map.json"),
                class_map: default_class_map(),
            },
            preprocessing: PreprocessingConfig {
                crop_rect: [0, 0, 1920, 1080], // フル画面
                resize_width: default_resize_width(),
                resize_height: default_resize_height(),
            },
            state: StateConfig {
                cooldown_seconds: default_cooldown_seconds(),
                required_consecutive: default_required_consecutive(),
            },
            server: ServerConfig {
                host: default_server_host(),
                port: default_server_port(),
            },
            detection: DetectionConfig {
                interval_ms: default_detection_interval_ms(),
            },
            screenshot: ScreenshotConfig {
                enabled: default_screenshot_enabled(),
                save_dir: default_screenshot_save_dir(),
            },
            debug: DebugConfig {
                enabled: default_debug_enabled(),
                save_dir: default_debug_save_dir(),
                save_cropped: default_debug_save_cropped(),
                save_preprocessed: default_debug_save_preprocessed(),
                save_results: default_debug_save_results(),
            },
        }
    }

    /// TOML文字列にシリアライズ（テンプレート生成用）
    #[allow(dead_code)]
    pub fn to_toml_string(&self) -> Result<String, ConfigError> {
        toml::to_string_pretty(self).map_err(|e| ConfigError::Serialize(e.to_string()))
    }

    /// クロップ領域をタプルとして取得
    pub fn crop_rect_tuple(&self) -> (u32, u32, u32, u32) {
        let rect = &self.preprocessing.crop_rect;
        (rect[0], rect[1], rect[2], rect[3])
    }
}

#[derive(Debug)]
pub enum ConfigError {
    FileRead(String, String),
    Parse(String, String),
    #[allow(dead_code)]
    Serialize(String),
}

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConfigError::FileRead(path, err) => {
                write!(f, "Failed to read config file '{}': {}", path, err)
            }
            ConfigError::Parse(path, err) => {
                write!(f, "Failed to parse config file '{}': {}", path, err)
            }
            ConfigError::Serialize(err) => {
                write!(f, "Failed to serialize config: {}", err)
            }
        }
    }
}

impl std::error::Error for ConfigError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default_with_required(
            "OBS Source".to_string(),
            PathBuf::from("models/model.onnx"),
        );

        assert_eq!(config.obs.host, "localhost");
        assert_eq!(config.obs.port, 4455);
        assert_eq!(config.obs.source_name, "OBS Source");
        assert_eq!(config.state.cooldown_seconds, 10);
        assert_eq!(config.state.required_consecutive, 3);
        assert_eq!(config.server.port, 3000);
    }

    #[test]
    fn test_serialize() {
        let config = Config::default_with_required(
            "OBS Source".to_string(),
            PathBuf::from("models/model.onnx"),
        );

        let toml = config.to_toml_string().unwrap();
        assert!(toml.contains("source_name"));
        assert!(toml.contains("model_path"));
    }

    #[test]
    fn test_crop_rect_tuple() {
        let config = Config::default_with_required(
            "OBS Source".to_string(),
            PathBuf::from("models/model.onnx"),
        );

        let (x, y, w, h) = config.crop_rect_tuple();
        assert_eq!((x, y, w, h), (0, 0, 1920, 1080));
    }
}
