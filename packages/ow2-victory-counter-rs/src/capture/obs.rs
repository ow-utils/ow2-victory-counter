use base64::{engine::general_purpose, Engine as _};
use image::DynamicImage;
use obws::{
    requests::sources::{SourceId, TakeScreenshot},
    Client as ObsClient,
};
use tracing::{debug, info};

#[derive(Debug)]
pub enum CaptureError {
    ObsConnection(String),
    ObsCapture(String),
    Base64Decode(String),
    ImageDecode(String),
    InvalidCrop(String),
}

impl std::fmt::Display for CaptureError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CaptureError::ObsConnection(e) => write!(f, "OBS connection error: {}", e),
            CaptureError::ObsCapture(e) => write!(f, "OBS capture error: {}", e),
            CaptureError::Base64Decode(e) => write!(f, "Base64 decode error: {}", e),
            CaptureError::ImageDecode(e) => write!(f, "Image decode error: {}", e),
            CaptureError::InvalidCrop(e) => write!(f, "Invalid crop parameters: {}", e),
        }
    }
}

impl std::error::Error for CaptureError {}

pub struct OBSCapture {
    client: ObsClient,
    source_name: String,
    width: u32,
    height: u32,
}

impl OBSCapture {
    /// OBS WebSocket に接続して OBSCapture インスタンスを作成
    pub async fn new(
        host: &str,
        port: u16,
        password: Option<&str>,
        source_name: String,
    ) -> Result<Self, CaptureError> {
        info!(
            "Connecting to OBS WebSocket at {}:{} for source '{}'",
            host, port, source_name
        );

        let client = ObsClient::connect(host, port, password)
            .await
            .map_err(|e| CaptureError::ObsConnection(e.to_string()))?;

        info!("Successfully connected to OBS WebSocket");

        Ok(Self {
            client,
            source_name,
            width: 1920,
            height: 1080,
        })
    }

    /// OBS から画像をキャプチャ (Base64 PNG として取得)
    pub async fn capture(&self) -> Result<DynamicImage, CaptureError> {
        debug!(
            "Capturing screenshot from source '{}' ({}x{})",
            self.source_name, self.width, self.height
        );

        // 1. OBS WebSocket 経由でスクリーンショット取得
        let image_data = self
            .client
            .sources()
            .take_screenshot(TakeScreenshot {
                source: SourceId::Name(&self.source_name),
                width: Some(self.width),
                height: Some(self.height),
                compression_quality: Some(-1), // PNG形式（非圧縮）
                format: "png",
            })
            .await
            .map_err(|e| CaptureError::ObsCapture(e.to_string()))?;

        // 2. Base64 デコード
        let base64_data = if image_data.starts_with("data:") {
            // "data:image/png;base64,..." 形式の場合、カンマ以降を抽出
            image_data
                .split(',')
                .nth(1)
                .ok_or_else(|| CaptureError::Base64Decode("Invalid data URL format".to_string()))?
        } else {
            &image_data
        };

        let png_bytes = general_purpose::STANDARD
            .decode(base64_data)
            .map_err(|e| CaptureError::Base64Decode(e.to_string()))?;

        debug!("Decoded {} bytes of PNG data", png_bytes.len());

        // 3. PNG デコード
        let image = image::load_from_memory_with_format(&png_bytes, image::ImageFormat::Png)
            .map_err(|e| CaptureError::ImageDecode(e.to_string()))?;

        debug!(
            "Successfully decoded image: {}x{}",
            image.width(),
            image.height()
        );

        Ok(image)
    }

    /// 画像の前処理 (クロップ)
    pub fn preprocess(
        &self,
        image: DynamicImage,
        crop_rect: (u32, u32, u32, u32),
    ) -> Result<DynamicImage, CaptureError> {
        let (x, y, width, height) = crop_rect;

        // クロップパラメータの検証
        if x + width > image.width() || y + height > image.height() {
            return Err(CaptureError::InvalidCrop(format!(
                "Crop region ({}x{} at {},{}) exceeds image dimensions ({}x{})",
                width,
                height,
                x,
                y,
                image.width(),
                image.height()
            )));
        }

        debug!(
            "Cropping image from ({}x{} at {},{}) to {}x{}",
            image.width(),
            image.height(),
            x,
            y,
            width,
            height
        );

        // クロップ実行
        let cropped = image.crop_imm(x, y, width, height);

        Ok(cropped)
    }



}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_crop_validation() {
        // テスト用のダミー画像を作成
        let dummy_image = DynamicImage::new_rgb8(1920, 1080);
        let capture = OBSCapture {
            client: unsafe { std::mem::zeroed() }, // テスト用ダミー
            source_name: "test".to_string(),
            width: 1920,
            height: 1080,
        };

        // 有効なクロップ
        let result = capture.preprocess(dummy_image.clone(), (0, 0, 100, 100));
        assert!(result.is_ok());

        // 無効なクロップ (範囲外)
        let result = capture.preprocess(dummy_image.clone(), (1900, 1000, 100, 100));
        assert!(result.is_err());
    }
}
