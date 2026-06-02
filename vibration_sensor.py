import RPi.GPIO as GPIO

VIBRATION_PIN = 10

def init_vibration(on_vibration_callback):
    """
    初始化震動感測器
    :param on_vibration_callback: 當觸發震動時，要回呼的外部函式
    """
    GPIO.setup(VIBRATION_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    
    try:
        GPIO.remove_event_detect(VIBRATION_PIN)
    except:
        pass
        
    # 註冊硬體中斷，監聽下墜邊緣（FALLING），設置 200ms 防彈跳雜訊
    GPIO.add_event_detect(
        VIBRATION_PIN, 
        GPIO.FALLING, 
        callback=on_vibration_callback, 
        bouncetime=200
    )
    print(f"[Vibration] 震動感測器初始化完畢，監聽 GPIO {VIBRATION_PIN}...")