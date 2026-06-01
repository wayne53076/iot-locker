# IoT Locker

## 專案簡介

這是一個基於 Raspberry Pi 的 IoT 櫃子鎖控系統，整合實體 4x4 鍵盤、繼電器鎖與 AWS IoT Shadow。使用者可以透過實體密碼或遠端 AWS IoT Shadow 指令解鎖櫃子，並在關門後自動上鎖。

## 功能

- 實體鍵盤解鎖
- 雲端遠端解鎖指令
- AWS IoT Shadow 狀態同步
- 門磁感測器監測門開/關狀態
- 自動上鎖防呆機制
- 密碼從雲端更新並同步回報

## 檔案說明

- `main.py`
  - 系統入口
  - 初始化 AWS IoT Shadow 客戶端
  - 啟動鍵盤掃描執行緒
  - 監控門感測器並維持雲端狀態
  - 觸發解鎖上鎖流程

- `keypad.py`
  - `KeypadManager` 4x4 矩陣鍵盤掃描
  - `#` 提交輸入密碼
  - `*` 清除輸入
  - 密碼正確時呼叫回調執行解鎖流程

- `lock_controll.py`
  - 繼電器鎖與門磁感測器 GPIO 控制
  - `lock()` / `unlock()` / `get_lock_status()` / `is_door_closed()`

- `shadow_client.py`
  - AWS IoT Shadow MQTT 連線封裝
  - `update_reported_state()` / `subscribe_to_delta()` / `sync_state()`
