@echo off
setlocal

set RUST_LOG=ow2_victory_detector=debug,ow2_victory_detector::capture=info,ow2_victory_detector::predictor=info
ow2-victory-detector.exe

endlocal
pause
