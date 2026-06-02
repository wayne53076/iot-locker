import cv2
import boto3
import threading
import time
import os

class CameraManager(threading.Thread):
    def __init__(self, bucket_name="你的-s3-bucket-名稱"):
        super().__init__()
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        self.pipeline = "libcamerasrc ! video/x-raw, width=640, height=480, framerate=14/1 ! videoconvert ! appsink"
        
        self.current_frame = None  # 儲存最新的相機畫面
        self.is_running = True
        self.is_uploading = False  # 判定是否正在上傳 S3
        self.daemon = True         # 主程式關閉時自動結束
        
        # 啟動相機硬體
        self.video_capture = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)
        if not self.video_capture.isOpened():
            print("[Camera] 嚴重錯誤：無法初始化相機硬體！")
            self.is_running = False

    def run(self):
        """
        背景守護執行緒：唯一有資格讀取相機硬體的迴圈，不斷更新 current_frame
        """
        print("[Camera] 📹 全域相機串流已啟動，正在維持即時畫面...")
        while self.is_running:
            ret, frame = self.video_capture.read()
            if ret:
                self.current_frame = frame
            time.sleep(0.05)  # 限制在每秒約 20 幀，降低 CPU 負載
            
        self.video_capture.release()

    def get_latest_frame(self):
        """
        提供給其他模組（例如人臉辨識）直接獲取當前畫面，完全不佔用硬體鎖
        """
        return self.current_frame

    def _upload_worker(self, frame_to_save, s3_key, local_tmp_path):
        """
        純粹處理圖片寫入與 S3 上傳的背景 Worker
        """
        try:
            cv2.imwrite(local_tmp_path, frame_to_save)
            print(f"[Camera] 正在將當下擷取的嫌犯照片送往 S3: {s3_key} ...")
            self.s3_client.upload_file(local_tmp_path, self.bucket_name, s3_key)
            print(f"[Camera] 嫌犯照片上傳成功！")
        except Exception as e:
            print(f"[Camera] 上傳 S3 失敗: {e}")
        finally:
            if os.path.exists(local_tmp_path):
                os.remove(local_tmp_path)
            self.is_uploading = False # 解除上傳鎖

    def capture_current_frame_to_s3_async(self, s3_key, prefix="intruder"):
        """
        震動觸發時呼叫：直接打包「當下那一幀」，瞬間開 Thread 上傳，完全不開關相機
        """
        if self.is_uploading:
            print("[Camera] 上一張照片還在傳輸中，忽略此次拍照請求。")
            return False

        if self.current_frame is None:
            print("[Camera] 錯誤：尚未取得有效的相機影格。")
            return False

        self.is_uploading = True
        
        # 複製當前畫面快照（Snapshot），防止後續迴圈改動到這張圖
        snapshot = self.current_frame.copy()
        local_tmp = f"{prefix}_{int(time.time())}.jpg"
        
        # 開執行緒只處理 S3 網路傳輸
        threading.Thread(
            target=self._upload_worker, 
            args=(snapshot, s3_key, local_tmp)
        ).start()
        return True