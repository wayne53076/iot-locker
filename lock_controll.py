import RPi.GPIO as GPIO
import time

# 設定腳位
RELAY_PIN = 17
SENSOR_PIN = 27

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- 狀態記憶變數 ---
last_door_state = None 
def get_lock_status():
    """
    讀取繼電器腳位的輸出狀態：
    HIGH (1) 代表目前處於解鎖狀態
    LOW (0) 代表目前處於上鎖狀態
    """
    state = GPIO.input(RELAY_PIN)
    if state == GPIO.HIGH:
        return "unlocked"
    else:
        return "locked"

def is_door_closed():
    """讀取門狀態：LOW 代表關閉 (磁簧開關觸發)"""
    return GPIO.input(SENSOR_PIN) == GPIO.LOW

def lock():
    if GPIO.input(RELAY_PIN) != GPIO.LOW: # 只有目前沒上鎖才執行
        print("[系統] 門已關閉，執行上鎖動作。")
        GPIO.output(RELAY_PIN, GPIO.LOW)

def unlock():
    if GPIO.input(RELAY_PIN) != GPIO.HIGH: # 只有目前沒解鎖才執行
        print("[系統] 門已開啟，保持解鎖狀態。")
        GPIO.output(RELAY_PIN, GPIO.HIGH)

# if __name__ == "__main__":
#     try:
#         while True:
#             current_door_closed = is_door_closed()

#             # --- 關鍵邏輯：只有狀態改變才輸出 ---
#             if current_door_closed != last_door_state:
#                 if current_door_closed:
#                     lock()
#                 else:
#                     unlock()
#                 last_door_state = current_door_closed # 更新最後狀態
            
#             time.sleep(0.5) # 稍微縮短檢查間隔，反應更靈敏

#     except KeyboardInterrupt:
#         print("\n[系統] 清理資源中...")
#         GPIO.cleanup()