import os
import subprocess
import boto3
import threading
import time

class CameraManager:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        self.is_uploading = False  # 判定是否正在上傳 S3

    def _upload_worker(self, local_tmp_path, s3_key):
        """
        純粹處理 S3 上傳的背景 Worker
        """
        try:
            print(f"[Camera] 儲存成功，正在將照片送往 S3: {s3_key} ...")
            self.s3_client.upload_file(local_tmp_path, self.bucket_name, s3_key)
            print(f"[Camera] 照片上傳成功！")
        except Exception as e:
            print(f"[Camera] 錯誤：上傳 S3 失敗: {e}")
        finally:
            if os.path.exists(local_tmp_path):
                os.remove(local_tmp_path)
            self.is_uploading = False # 解除上傳鎖

    def capture_current_frame_to_s3_async(self, s3_key, prefix="intruder"):
        """
        震動觸發時呼交：直接叫系統拍照並非同步上傳
        """
        if self.is_uploading:
            print("[Camera] 上一張照片還在傳輸中，忽略此次拍照請求。")
            return False

        self.is_uploading = True
        local_tmp = f"{prefix}_{int(time.time())}.jpg"

        # --immediate: 立即拍照不用等待曝光
        # --width / --height: 指定解析度
        # -o: 輸出路徑
        cmd = f"rpicam-still --immediate --width 640 --height 480 -e jpg -o {local_tmp}"
        
        try:
            # 這裡用 subprocess 執行拍照，拍照通常在一秒內完成
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 拍完之後，開執行緒只處理 S3 網路傳輸，完全不卡主程式
            threading.Thread(
                target=self._upload_worker, 
                args=(local_tmp, s3_key)
            ).start()
            return True
        except Exception as e:
            print(f"[Camera] 系統原生拍照失敗: {e}")
            self.is_uploading = False
            return False