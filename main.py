import time
import json
import RPi.GPIO as GPIO
from shadow_client import ShadowClient
import lock_controll as hw
from keypad import KeypadManager

# 配置參數 (請根據你的 AWS IoT 環境修改)
CONFIG = {
    "endpoint": "a1x8e9kvaznd4d-ats.iot.ap-northeast-1.amazonaws.com",
    "cert": "certs/certificate.pem.crt",
    "key": "certs/private.pem.key",
    "root_ca": "certs/AmazonRootCA1.pem",
    "client_id": "RaspberryPi_Box_01",
    "thing_name": "locker-pi"
}

def execute_unlock_sequence(trigger_source="未知"):
    """
    統一的解鎖精靈：處理實體開門緩衝與關門上鎖流程。
    """
    current_physical_status = hw.get_lock_status()
    if current_physical_status == "unlocked":
        print(f"[系統] 來自 [{trigger_source}] 的指令：櫃門已在解鎖狀態，忽略動作。")
        return

    print(f"[系統] 觸發來源: [{trigger_source}]，準備解鎖...")
    hw.unlock()
    
    # 開門緩衝邏輯
    open_buffer = 30
    has_opened = False
    print(f"[系統] 已解鎖，請在 {open_buffer} 秒內開啟櫃門...")
    
    while open_buffer > 0:
        if not hw.is_door_closed():
            has_opened = True
            print("[系統] 偵測到門已開啟")
            break
        time.sleep(1)
        open_buffer -= 1

    if has_opened:
        timeout = 30 
        while not hw.is_door_closed() and timeout > 0:
            print(f"等待使用者放完東西並關門中...剩餘 {timeout} 秒")
            time.sleep(1)
            timeout -= 1
        
        print("[系統] 偵測到歸還關門，執行上鎖")
        hw.lock()
    else:
        print("[防呆] 使用者逾時未開門，自動重新上鎖以策安全")
        hw.lock()

    # 無論如何，最後與雲端同步為最新安全狀態
    client.sync_state(
        reported_dict={"lock_status": "locked", "door_sensor": "closed"}, 
        clear_keys=["lock_status"]
    )

def on_lock_state_delta(delta_state):
    if "lock_status" in delta_state:
        target_status = delta_state["lock_status"]
        if target_status is None: 
            return
        
        if target_status == "unlocked":
            execute_unlock_sequence(trigger_source="雲端遠端")
        elif target_status == "locked":
            hw.lock()
            client.sync_state(reported_dict={"lock_status": "locked"}, clear_keys=["lock_status"])

def on_keypad_success():
    """鍵盤來的成功通知"""
    execute_unlock_sequence(trigger_source="實體鍵盤")
            
def main():
    global client
    GPIO.setmode(GPIO.BCM)
    # 初始化 Shadow 客戶端[cite: 2]
    locker_id = "1"
    client = ShadowClient(**CONFIG, shadow_name=locker_id)
    # 訂閱 Delta 更新[cite: 2]
    initial_status = {
        "init": True,
        "lock_status": "locked", 
        "door_sensor": "closed" if hw.is_door_closed() else "open"
    }
    client.update_reported_state(initial_status)
    client.subscribe_to_delta(on_lock_state_delta)
    last_door_status = "closed" if hw.is_door_closed() else "open"
    hw.lock() # 確保一開始是上鎖狀態

    print("系統已啟動，監聽 AWS IoT 指令中...")
    keypad_thread = KeypadManager(password="1234", on_success_callback=on_keypad_success)
    keypad_thread.daemon = True  # 當主程式關閉時，執行緒一起結束
    keypad_thread.start()

    last_door_status = "closed" if hw.is_door_closed() else "open"
    print("系統已啟動，監聽 AWS IoT 與實體鍵盤指令中...")
    # 主迴圈：持續監控感測器狀態並定期回報 (對應 listen Sensor status)
    try:
        while True:
            current_door_status = "closed" if hw.is_door_closed() else "open"

            if current_door_status != last_door_status:
                # print(f"[狀態變更] 偵測到門狀態變為: {current_door_status}，更新雲端...")
                # client.update_reported_state({"door_sensor": current_door_status})
                
                last_door_status = current_door_status
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("停止程式")

if __name__ == "__main__":
    main()