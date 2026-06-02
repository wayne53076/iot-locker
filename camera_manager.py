import cv2
import boto3
import threading
import time
import os

class CameraManager:
    def __init__(self, bucket_name="你的-s3-bucket-名稱"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        self.pipeline = "libcamerasrc ! video/x-raw, width=640, height=480, framerate=14/1 ! videoconvert ! appsink"
        
        self.is_capturing = False

    def _capture_and_upload_worker(self, s3_key, local_tmp_path):
        """
        實際在背景執行的 Worker
        """
        try:
            print("[Camera] 正在啟動相機...")
            video_capture = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)

            if not video_capture.isOpened():
                print("[Camera] 錯誤：無法開啟相機資源。")
                return

            frame = None
            for _ in range(5):
                ret, frame = video_capture.read()
                
            video_capture.release() 

            if frame is not None:
                cv2.imwrite(local_tmp_path, frame)
                try:
                    print(f"[Camera] 正在將照片上傳至 S3: {s3_key} ...")
                    self.s3_client.upload_file(local_tmp_path, self.bucket_name, s3_key)
                    print(f"[Camera] 🎉 照片上傳成功！")
                except Exception as e:
                    print(f"[Camera] 錯誤：上傳 S3 失敗: {e}")
                finally:
                    if os.path.exists(local_tmp_path):
                        os.remove(local_tmp_path)
            else:
                print("[Camera] 錯誤：擷取相機畫面失敗。")
                
        finally:
            self.is_capturing = False

    def capture_to_s3_async(self, s3_key, prefix="img"):
        """
        非同步介面：如果目前正在拍照，會直接拒絕新任務，避免塞車
        """
        # 1. 檢查目前是否正在拍照或上傳
        if self.is_capturing:
            print("[Camera] ⏳ 上一筆照片還在傳，忽略此次拍照請求，避免硬體塞車。")
            return False # 回傳 False 告訴外部沒成功啟動
            
        # 2. 如果沒在工作，立刻上鎖並開 Thread
        self.is_capturing = True
        local_tmp = f"{prefix}_{int(time.time())}.jpg"
        
        task = threading.Thread(
            target=self._capture_and_upload_worker, 
            args=(s3_key, local_tmp)
        )
        task.start()
        return True # 成功啟動任務