use serde::{Deserialize, Serialize};
use std::time::Instant;
use tokio::sync::broadcast;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    Ready,
    Cooldown,
    WaitingForNone,
}

/// 検知結果
#[derive(Debug, Clone, Copy)]
pub struct DetectionResult {
    /// イベントがトリガーされたか（カウントが確定したか）
    pub event_triggered: bool,
    /// 連続検知の最初の1回か（スクリーンショット保存用）
    pub is_first_detection: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CounterUpdate {
    pub victories: u32,
    pub defeats: u32,
    pub draws: u32,
    pub last_outcome: Option<String>,
    pub timestamp: f64,
}

pub struct StateManager {
    state: State,
    victories: u32,
    defeats: u32,
    draws: u32,
    cooldown_seconds: u64,
    required_consecutive: usize,
    consecutive_detections: Vec<String>,
    last_event_time: Option<Instant>,
    broadcast_tx: broadcast::Sender<CounterUpdate>,
}

impl StateManager {
    pub fn new(cooldown_seconds: u64, required_consecutive: usize) -> Self {
        let (broadcast_tx, _) = broadcast::channel(100);

        Self {
            state: State::Ready,
            victories: 0,
            defeats: 0,
            draws: 0,
            cooldown_seconds,
            required_consecutive,
            consecutive_detections: Vec::new(),
            last_event_time: None,
            broadcast_tx,
        }
    }

    pub fn subscribe(&self) -> broadcast::Receiver<CounterUpdate> {
        self.broadcast_tx.subscribe()
    }

    pub fn record_detection(&mut self, outcome: &str) -> DetectionResult {
        let mut result = DetectionResult {
            event_triggered: false,
            is_first_detection: false,
        };

        match self.state {
            State::Ready => {
                if outcome != "none" {
                    self.consecutive_detections.push(outcome.to_string());

                    // 連続検知の最初の1回
                    if self.consecutive_detections.len() == 1 {
                        result.is_first_detection = true;
                    }

                    if self.consecutive_detections.len() >= self.required_consecutive {
                        // カウント確定
                        self.increment_counter(outcome);
                        self.state = State::Cooldown;
                        self.last_event_time = Some(Instant::now());
                        self.consecutive_detections.clear();

                        // SSE配信
                        self.broadcast_update(Some(outcome.to_string()));
                        result.event_triggered = true;
                    }
                } else {
                    self.consecutive_detections.clear();
                }
            }
            State::Cooldown => {
                if let Some(last_time) = self.last_event_time {
                    if last_time.elapsed().as_secs() >= self.cooldown_seconds {
                        if outcome != "none" {
                            self.state = State::WaitingForNone;
                        } else {
                            self.state = State::Ready;
                        }
                    }
                }
            }
            State::WaitingForNone => {
                if outcome == "none" {
                    self.state = State::Ready;
                }
            }
        }

        result
    }

    fn increment_counter(&mut self, outcome: &str) {
        match outcome {
            "victory" => self.victories += 1,
            "defeat" => self.defeats += 1,
            "draw" => self.draws += 1,
            _ => {}
        }
    }

    pub fn initialize(&mut self, victories: u32, defeats: u32, draws: u32) {
        self.victories = victories;
        self.defeats = defeats;
        self.draws = draws;
        self.broadcast_update(None);
    }

    pub fn adjust(&mut self, outcome: &str, delta: i32) {
        match outcome {
            "victory" => self.victories = (self.victories as i32 + delta).max(0) as u32,
            "defeat" => self.defeats = (self.defeats as i32 + delta).max(0) as u32,
            "draw" => self.draws = (self.draws as i32 + delta).max(0) as u32,
            _ => {}
        }
        self.broadcast_update(Some(outcome.to_string()));
    }

    fn broadcast_update(&self, last_outcome: Option<String>) {
        let update = CounterUpdate {
            victories: self.victories,
            defeats: self.defeats,
            draws: self.draws,
            last_outcome,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
        };

        let _ = self.broadcast_tx.send(update);
    }

    pub fn summary(&self) -> CounterUpdate {
        CounterUpdate {
            victories: self.victories,
            defeats: self.defeats,
            draws: self.draws,
            last_outcome: None,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
        }
    }
}
