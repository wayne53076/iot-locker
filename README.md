# IoT Locker

## 專案簡介

這是一個基於 Raspberry Pi 的智慧櫃子鎖控系統，整合實體 4x4 鍵盤、門磁感測器、震動防盜、繼電器鎖以及 AWS IoT Shadow。系統支援本地密碼解鎖、雲端遠端解鎖、一次性密碼更新以及照相事件上傳。

## 主要功能

- 實體鍵盤密碼解鎖
- AWS IoT Shadow 雲端遠端解鎖指令
- 雲端同步密碼與鎖狀態
- 門磁感測器監測門開/關狀態
- 開門後自動上鎖流程
- 震動感測器異常警報偵測
- 相機拍照並上傳至 AWS S3（人臉驗證/異常事件）

## 執行流程

1. `main.py` 會初始化 GPIO、鎖控硬體、AWS Shadow 連線、攝影機與震動感測器。
2. 啟動 `KeypadManager` 監聽實體鍵盤輸入。
3. 接收雲端 Shadow delta 指令，處理解鎖或密碼更新。
4. 解除鎖定後，系統等待使用者開門與關門，再自動上鎖。
5. 震動感測器偵測到非正常震動時，會觸發相機拍照並上傳 S3。

## 模組說明

- `main.py`
  - 系統入口
  - 初始化 AWS IoT Shadow 客戶端與 MQTT 訂閱
  - 啟動鍵盤、攝影機與震動感測器
  - 管理解鎖流程與狀態同步

- `keypad.py`
  - `KeypadManager` 4x4 矩陣鍵盤掃描
  - `#` 按鍵提交密碼，`*` 清除輸入
  - 成功驗證時呼叫 `on_keypad_success()` 解鎖流程
  - 支援按下 `A` 鍵觸發人臉解鎖照片請求

- `lock_controll.py`
  - 繼電器鎖與門磁感測器 GPIO 控制
  - `init_hardware()` 初始化腳位設定
  - `lock()`、`unlock()`、`get_lock_status()`、`is_door_closed()`

- `shadow_client.py`
  - AWS IoT Shadow MQTT 連線與 Topic 封裝
  - 監聽 `delta` 指令、回報 `reported` 狀態
  - `update_reported_state()`、`clear_desired_state()`、`sync_state()`

- `camera_manager.py`
  - 使用 Pi Camera 拍照並非同步上傳到 AWS S3
  - `capture_current_frame_to_s3_async()` 用於異常與人臉請求攝影

- `vibration_sensor.py`
  - 初始震動感測器 GPIO
  - 註冊硬體中斷回呼以偵測破壞性震動

## 硬體需求

- Raspberry Pi
- 4x4 矩陣鍵盤
- 繼電器鎖模組
- 門磁感應開關
- 震動感測器
- Pi Camera 模組

## 使用方式

1. 安裝 Python 與所需套件
2. 建立 `certs/` 資料夾並放入 AWS IoT 憑證
3. 修改 `main.py` 中的 `CONFIG` 與 S3 bucket 名稱
4. 執行：

```bash
python main.py
```
