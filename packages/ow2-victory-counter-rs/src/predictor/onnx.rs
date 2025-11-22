use image::DynamicImage;
use ndarray::Array4;
use ort::{
    session::{builder::GraphOptimizationLevel, Session},
    value::Value,
};
use serde::Deserialize;
use std::collections::HashMap;
use tracing::{debug, info};

#[derive(Debug)]
pub enum PredictionError {
    ModelLoad(String),
    LabelMapLoad(String),
    Inference(String),

}

impl std::fmt::Display for PredictionError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PredictionError::ModelLoad(e) => write!(f, "Model load error: {}", e),
            PredictionError::LabelMapLoad(e) => write!(f, "Label map load error: {}", e),
            PredictionError::Inference(e) => write!(f, "Inference error: {}", e),

        }
    }
}

impl std::error::Error for PredictionError {}

#[derive(Debug, Clone)]
pub struct Detection {
    pub outcome: String,
    pub confidence: f32,
    pub predicted_class: String,
    pub probabilities: Vec<(String, f32)>,
}

/// label_map.json ファイルの構造を表す構造体
#[derive(Debug, Deserialize)]
struct LabelMapFile {
    #[allow(dead_code)]
    label_map: HashMap<String, usize>,
    #[serde(deserialize_with = "deserialize_idx_to_label")]
    idx_to_label: HashMap<usize, String>,
}

/// idx_to_label の文字列キーを usize に変換するカスタムデシリアライザー
fn deserialize_idx_to_label<'de, D>(deserializer: D) -> Result<HashMap<usize, String>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    let string_map: HashMap<String, String> = HashMap::deserialize(deserializer)?;
    string_map
        .into_iter()
        .map(|(k, v)| {
            k.parse::<usize>()
                .map(|key| (key, v))
                .map_err(serde::de::Error::custom)
        })
        .collect()
}

pub struct VictoryPredictor {
    session: Session,
    label_map: HashMap<usize, String>,
}

impl VictoryPredictor {
    /// ONNX モデルとラベルマップを読み込んで VictoryPredictor を作成
    pub fn new(model_path: &str, label_map_path: &str) -> Result<Self, PredictionError> {
        info!("Loading ONNX model from: {}", model_path);

        // ONNX Session の初期化
        let session = Session::builder()
            .map_err(|e| PredictionError::ModelLoad(e.to_string()))?
            .with_optimization_level(GraphOptimizationLevel::Level3)
            .map_err(|e| PredictionError::ModelLoad(e.to_string()))?
            .commit_from_file(model_path)
            .map_err(|e| PredictionError::ModelLoad(e.to_string()))?;

        info!("ONNX model loaded successfully");

        // label_map 読み込み
        info!("Loading label map from: {}", label_map_path);
        let label_map_json = std::fs::read_to_string(label_map_path)
            .map_err(|e| PredictionError::LabelMapLoad(e.to_string()))?;

        let label_map_file: LabelMapFile = serde_json::from_str(&label_map_json)
            .map_err(|e| PredictionError::LabelMapLoad(e.to_string()))?;
        let label_map = label_map_file.idx_to_label;

        info!("Label map loaded: {:?}", label_map);

        Ok(Self {
            session,
            label_map,
        })
    }

    /// softmax関数: logitsを確率に変換
    fn softmax(logits: &[f32]) -> Vec<f32> {
        // 数値安定性のため、最大値を引く
        let max_logit = logits.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

        // exp(x - max)を計算
        let exp_values: Vec<f32> = logits.iter().map(|&x| (x - max_logit).exp()).collect();

        // 合計を計算
        let sum: f32 = exp_values.iter().sum();

        // 正規化
        exp_values.iter().map(|&x| x / sum).collect()
    }

    /// 画像から勝敗を推論
    pub fn predict(&mut self, image: &DynamicImage) -> Result<Detection, PredictionError> {
        debug!(
            "Running prediction on image: {}x{}",
            image.width(),
            image.height()
        );

        // 1. 画像をテンソルに変換 (HWC → CHW, RGB, 正規化)
        let tensor = self.image_to_tensor(image)?;

        // 2. テンソルを Value に変換
        let value = Value::from_array(tensor)
            .map_err(|e| PredictionError::Inference(format!("Failed to create value: {}", e)))?;

        // 3. ONNX Runtime 推論
        let (_class_idx, confidence, predicted_class, probabilities) = {
            let outputs = self
                .session
                .run(ort::inputs![value])
                .map_err(|e| PredictionError::Inference(e.to_string()))?;

            // 4. 出力（logits）を取得
            let output_tensor = outputs[0]
                .try_extract_array::<f32>()
                .map_err(|e| PredictionError::Inference(format!("Failed to extract tensor: {}", e)))?;

            let logits = output_tensor.as_slice().ok_or_else(|| {
                PredictionError::Inference("Failed to get tensor as slice".to_string())
            })?;

            // 5. softmax適用: logits -> 確率
            let probs = Self::softmax(logits);

            // 6. 最大確率のクラスを取得
            let (class_idx, &confidence) = probs
                .iter()
                .enumerate()
                .max_by(|(_, a), (_, b)| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal))
                .ok_or_else(|| {
                    PredictionError::Inference("No predictions returned".to_string())
                })?;

            // クラス ID をラベルに変換
            let predicted_class = self
                .label_map
                .get(&class_idx)
                .cloned()
                .unwrap_or_else(|| format!("unknown_{}", class_idx));

            // 7. 全クラスの確率をラベルとペアにする
            let probabilities: Vec<(String, f32)> = probs
                .iter()
                .enumerate()
                .map(|(idx, &prob)| {
                    let label = self
                        .label_map
                        .get(&idx)
                        .cloned()
                        .unwrap_or_else(|| format!("unknown_{}", idx));
                    (label, prob)
                })
                .collect();

            (class_idx, confidence, predicted_class, probabilities)
        };

        let outcome = Self::class_to_outcome(&predicted_class);

        debug!(
            "Prediction: class={}, outcome={}, confidence={:.4}",
            predicted_class, outcome, confidence
        );

        Ok(Detection {
            outcome,
            confidence,
            predicted_class,
            probabilities,
        })
    }

    /// 画像を NCHW テンソルに変換 (N=1, C=3, H=height, W=width)
    /// ONNXモデルが期待するサイズ（283x512）にリサイズする
    fn image_to_tensor(&self, image: &DynamicImage) -> Result<Array4<f32>, PredictionError> {
        const TARGET_WIDTH: u32 = 512;
        const TARGET_HEIGHT: u32 = 283;

        debug!(
            "Original image size: {}x{}, resizing to {}x{}",
            image.width(), image.height(), TARGET_WIDTH, TARGET_HEIGHT
        );

        // モデルが期待するサイズにリサイズ
        let resized = image.resize_exact(
            TARGET_WIDTH,
            TARGET_HEIGHT,
            image::imageops::FilterType::Triangle,
        );

        let rgb_image = resized.to_rgb8();

        debug!(
            "Converting image to tensor: {}x{} RGB",
            TARGET_WIDTH, TARGET_HEIGHT
        );

        // NCHW 形式のテンソルを作成
        let mut tensor = Array4::<f32>::zeros((1, 3, TARGET_HEIGHT as usize, TARGET_WIDTH as usize));

        // HWC (image) → CHW (tensor) 変換 + 正規化 (0-255 → 0-1)
        for y in 0..TARGET_HEIGHT {
            for x in 0..TARGET_WIDTH {
                let pixel = rgb_image.get_pixel(x, y);
                tensor[[0, 0, y as usize, x as usize]] = pixel[0] as f32 / 255.0; // R
                tensor[[0, 1, y as usize, x as usize]] = pixel[1] as f32 / 255.0; // G
                tensor[[0, 2, y as usize, x as usize]] = pixel[2] as f32 / 255.0; // B
            }
        }

        Ok(tensor)
    }

    /// クラス名を outcome に変換
    fn class_to_outcome(class: &str) -> String {
        match class {
            "victory_text" | "victory_progressbar" => "victory".to_string(),
            "defeat_text" | "defeat_progressbar" => "defeat".to_string(),
            "none" => "none".to_string(),
            _ => "none".to_string(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;


    #[test]
    fn test_class_to_outcome() {
        assert_eq!(VictoryPredictor::class_to_outcome("victory_text"), "victory");
        assert_eq!(VictoryPredictor::class_to_outcome("victory_progressbar"), "victory");
        assert_eq!(VictoryPredictor::class_to_outcome("defeat_text"), "defeat");
        assert_eq!(VictoryPredictor::class_to_outcome("defeat_progressbar"), "defeat");
        assert_eq!(VictoryPredictor::class_to_outcome("none"), "none");
        assert_eq!(VictoryPredictor::class_to_outcome("unknown"), "none");
    }
}
