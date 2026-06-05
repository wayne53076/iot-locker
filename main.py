import time
import json
import threading
import RPi.GPIO as GPIO
from shadow_client import ShadowClient
import lock_controll as hw
from keypad import KeypadManager
import vibration_sensor as vib
import camera_manager as cam

CONFIG = {
    "endpoint": "a1x8e9kvaznd4d-ats.iot.ap-northeast-1.amazonaws.com",
    "cert": "certs/certificate.pem.crt",
    "key": "certs/private.pem.key",
    "root_ca": "certs/AmazonRootCA1.pem",
    "client_id": "RaspberryPi_Box_01",
    "thing_name": "locker-pi"
}

lock_sequence_mutex = threading.Lock()

def execute_unlock_sequence(trigger_source="未知"):
    """
    統一的解鎖精靈：處理實體開門緩衝與關門上鎖流程。
    """
    with lock_sequence_mutex:
        current_physical_status = hw.get_lock_status()
        if current_physical_status == "unlocked":
            print(f"[系統] 來自 [{trigger_source}] 的指令：櫃門已在解鎖狀態，忽略動作。")
            return

        print(f"[系統] 觸發來源: [{trigger_source}]，準備解鎖...")
        hw.unlock()
        
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
            
            if hw.is_door_closed():
                print("[系統] 偵測到歸還關門，執行上鎖")
            else:
                print("[警告] 使用者未關門超時！強制伸出鎖舌")
            hw.lock()
        else:
            print("[防呆] 使用者逾時未開門，自動重新上鎖以策安全")
            hw.lock()

        actual_lock = hw.get_lock_status()
        actual_door = "closed" if hw.is_door_closed() else "open"
        client.sync_state(
            reported_dict={"lock_status": actual_lock, "door_sensor": actual_door}, 
            clear_keys=["lock_status"]
        )

def on_lock_state_delta(delta_state):
    global keypad_thread
    if "lock_status" in delta_state:
        target_status = delta_state["lock_status"]
        if target_status == "unlocked":
            threading.Thread(target=execute_unlock_sequence, kwargs={"trigger_source": "雲端遠端"}).start()
            
    if "password" in delta_state:
        new_pwd = delta_state["password"]
        if new_pwd is None:
            return
            
        print(f"[系統] 收到雲端密碼變更指令，新密碼: {new_pwd}")
        keypad_thread.update_password(new_pwd)
        
        client.sync_state(
            reported_dict={"password": new_pwd},
            clear_keys=["password"]
        )

def on_keypad_success():
    global keypad_thread, client
    threading.Thread(target=execute_unlock_sequence, kwargs={"trigger_source": "實體鍵盤"}).start()
    print("[系統] 一次性密碼驗證成功，密碼已失效。")
    keypad_thread.update_password(None)
    client.sync_state(
        reported_dict={"password": None, "status": "used"},
        clear_keys=["password"]
    )

def on_face_unlock_requested():
    """
    當使用者按下 A 鍵時觸發：拍照並非同步上傳至 S3 requests/ 資料夾
    """
    timestamp = int(time.time())
    # 存放在 requests/ 虛擬目錄下，供雲端 S3 監聽觸發 Lambda 辨識
    s3_path = f"requests/unlock_{client.shadow_name}_{timestamp}.jpg"
    
    print("[人臉解鎖] 正在擷取現場影像並非同步上傳至雲端...")
    success = camera.capture_current_frame_to_s3_async(s3_key=s3_path, prefix="face_req")
    
    if success:
        print("[人臉解鎖] 請求已成功派發，請面向相機等待雲端比對結果...")
    else:
        print("[人臉解鎖] 錯誤：相機模組忙碌中，請稍後再試。")

# 2. 定義震動觸發時的業務邏輯
def on_vibration_triggered(channel):
    """
    震動硬體中斷回呼：由震動感測器模組觸發
    """
    # 核心邏輯：如果非處於解鎖精靈期間（Mutex 沒被鎖定），代表是異常破壞
    if not lock_sequence_mutex.locked():
        timestamp = int(time.time())
        print(f"[警報] 偵測到異常震動！非解鎖期間觸發，企圖破壞櫃子！時間：{time.strftime('%H:%M:%S')}")

        s3_path = f"alarms/locker_{client.shadow_name}_{timestamp}.jpg"
        camera.capture_current_frame_to_s3_async(s3_key=s3_path)
    else:
        # 如果解鎖精靈正在跑，使用者開關門本來就會大力震動，此處選擇忽略，避免誤報
        print("[系統] 偵測到震動，但目前處於正常解鎖取開門期間，忽略此雜訊。")

def main():
    global client, keypad_thread, camera
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    hw.init_hardware()
    hw.lock() 

    # 初始化 AWS Shadow 客戶端
    locker_id = "1"
    client = ShadowClient(**CONFIG, shadow_name=locker_id)
    
    initial_status = {
        "init": True,
        "lock_status": hw.get_lock_status(), 
        "door_sensor": "closed" if hw.is_door_closed() else "open"
    }
    client.update_reported_state(initial_status)
    client.subscribe_to_delta(on_lock_state_delta)

    camera = cam.CameraManager(bucket_name="iot-locker-photo-storage--632295790221-ap-northeast-1-an")
    vib.init_vibration(on_vibration_callback=on_vibration_triggered)

    # 初始化並啟動實體鍵盤
    keypad_thread = KeypadManager(on_success_callback=on_keypad_success, on_face_request_callback=on_face_unlock_requested)
    keypad_thread.daemon = True  
    keypad_thread.start()

    print("系統已啟動，監聽 AWS IoT、實體鍵盤與震動防盜中...")
    
    last_door_status = "closed" if hw.is_door_closed() else "open"
    
    try:
        while True:
            current_door_status = "closed" if hw.is_door_closed() else "open"

            # 突發破門監控
            if current_door_status != last_door_status:
                if not lock_sequence_mutex.locked():
                    print(f"[狀態突變] 偵測到門狀態變為: {current_door_status}，同步到雲端...")
                    client.update_reported_state({"door_sensor": current_door_status})
                last_door_status = current_door_status
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("停止程式")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()