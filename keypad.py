import RPi.GPIO as GPIO
import time
import threading

class KeypadManager(threading.Thread):
    def __init__(self, password="1234", on_success_callback=None):
        super().__init__()
        self.ROW_PINS = [5, 6, 13, 19]
        self.COL_PINS = [26, 16, 20, 21]
        self.PASSWORD = password
        self.on_success_callback = on_success_callback
        self.input_buffer = ""
        self.is_running = True
        self.keys = [
            ["1", "2", "3", "A"],
            ["4", "5", "6", "B"],
            ["7", "8", "9", "C"],
            ["*", "0", "#", "D"]
        ]
        for pin in self.ROW_PINS:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        for pin in self.COL_PINS:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def run(self):
        """執行緒啟動後會跑這裡，不會卡死主程式"""
        print("[Keypad] 實體鍵盤掃描執行緒已啟動...")
        while self.is_running:
            for r_idx, r_pin in enumerate(self.ROW_PINS):
                GPIO.output(r_pin, GPIO.LOW)

                for c_idx, c_pin in enumerate(self.COL_PINS):
                    if GPIO.input(c_pin) == GPIO.LOW:
                        key = self.keys[r_idx][c_idx]
                        
                        if key == "#":
                            if self.input_buffer == self.PASSWORD:
                                print("\n[Keypad] 實體密碼正確！")
                                if self.on_success_callback:
                                    # 觸發外部傳入的解鎖流程
                                    self.on_success_callback()
                            else:
                                print("\n[Keypad] 密碼錯誤！")
                            self.input_buffer = ""
                        
                        elif key == "*":
                            print("\n[Keypad] 已清除輸入。")
                            self.input_buffer = ""
                        
                        else:
                            self.input_buffer += key
                            print(f"\r[Keypad] 目前輸入: {'*' * len(self.input_buffer)}", end="", flush=True)

                        while GPIO.input(c_pin) == GPIO.LOW:
                            time.sleep(0.05)
                
                GPIO.output(r_pin, GPIO.HIGH)
            time.sleep(0.02)

    def stop(self):
        self.is_running = False