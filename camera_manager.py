import cv2
import boto3
import threading
import time
import os

class CameraManager:
    def __init__(self, bucket_name="iot-locker-photo-storage--632295790221-ap-northeast-1-an"):
        """
        初始化相機管理模組
        :param bucket_name: Amazon S3 的儲存桶名稱
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        # 新版樹莓派系統 (Bookworm) OpenCV 呼叫 V2 相機的標準管道設定
        self.pipeline = "libcamerasrc ! video/x-raw, width=640, height=480, framerate=14/1 ! videoconvert ! appsink"

    def _capture_and_upload_worker(self, s3_key, local_tmp_path="temp_img.jpg"):
        """
        實際在背景執行的背景 Worker：負責拍照與上傳，避免卡死主執行緒
        """
        print("[Camera] 正在啟動相機...")
        video_capture = cv2.VideoCapture(self.pipeline, cv2.CAP_GSTREAMER)

        if not video_capture.isOpened():
            print("[Camera] 錯誤：無法開啟相機資源。")
            return

        # 稍微等相機曝光穩定，抓取第 5 幀快門
        frame = None
        for _ in range(5):
            ret, frame = video_capture.read()
            
        video_capture.release()  # 拍照完立刻釋放硬體鎖

        if frame is not None:
            # 儲存為本地暫存檔
            cv2.imwrite(local_tmp_path, frame)
            
            try:
                print(f"[Camera] 正在將照片上傳至 S3: {s3_key} ...")
                self.s3_client.upload_file(local_tmp_path, self.bucket_name, s3_key)
                print(f"[Camera] 🎉 照片上傳成功！")
            except Exception as e:
                print(f"[Camera] 錯誤：上傳 S3 失敗: {e}")
            finally:
                # 刪除本地暫存檔，維持空間乾淨
                if os.path.exists(local_tmp_path):
                    os.remove(local_tmp_path)
        else:
            print("[Camera] 錯誤：擷取相機畫面失敗。")

    def capture_to_s3_async(self, s3_key, prefix="img"):
        """
        對外公開的非同步介面：丟了這個函式後，它會自動開執行緒去處理，完全不卡主程式
        :param s3_key: 存放在 S3 上的完整路徑與檔名 (例如: almarms/locker_1_12345.jpg)
        :param prefix: 用於區隔本地暫存檔檔名的前綴字
        """
        local_tmp = f"{prefix}_{int(time.time())}.jpg"
        
        # 開啟全新的背景執行緒執行拍照任務
        task = threading.Thread(
            target=self._capture_and_upload_worker, 
            args=(s3_key, local_tmp)
        )
        task.start()