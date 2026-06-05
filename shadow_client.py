import json
import time
from awscrt import mqtt
from awsiot import mqtt_connection_builder

class ShadowClient:
    def __init__(self, endpoint, cert, key, root_ca, client_id, thing_name, shadow_name):
        self.thing_name = thing_name
        self.shadow_name = str(shadow_name)
        
        # 1. 建立 MQTT 連線
        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=endpoint,
            cert_filepath=cert,
            pri_key_filepath=key,
            ca_filepath=root_ca,
            client_id=client_id,
            clean_session=False,
            keep_alive_secs=30
        )
        self.connect_future = self.mqtt_connection.connect()
        self.connect_future.result()
        
        self.delta_callback = None
        
        # 定義影子相關的 MQTT Topics
        self.base_topic = f"$aws/things/{self.thing_name}/shadow/name/{self.shadow_name}"
        self.update_topic = f"{self.base_topic}/update"
        self.delta_topic = f"{self.base_topic}/update/delta"

    def subscribe_to_delta(self, callback):
        """直接透過 MQTT 訂閱 Delta 主題"""
        self.delta_callback = callback
        print(f"[{self.shadow_name}號櫃] 正在訂閱 MQTT Delta: {self.delta_topic}")
        
        subscribe_future, _ = self.mqtt_connection.subscribe(
            topic=self.delta_topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=self._on_mqtt_delta_received
        )
        subscribe_future.result()

    def _on_mqtt_delta_received(self, topic, payload, dup, qos, retain, **kwargs):
        """處理接收到的 MQTT Delta 原始訊息"""
        try:
            payload_dict = json.loads(payload.decode('utf-8'))
            
            # 檢查 state 是否存在
            if "state" in payload_dict:
                delta_content = payload_dict["state"]
                # 修改這裡：直接把 delta 的 JSON 內容轉成明文字串印出來
                print(f"[{self.shadow_name}號櫃] 收到原始 Delta 訊息！內容: {json.dumps(delta_content, ensure_ascii=False)}")
                
                if self.delta_callback:
                    self.delta_callback(delta_content)
            else:
                print(f"[{self.shadow_name}號櫃] 收到 Delta 訊息，但未包含有效的 'state' 鍵值。")
                
        except Exception as e:
            print(f"解析 Delta 訊息失敗: {e}")

    def update_reported_state(self, reported_dict):
        """手動發送符合 Shadow 規範的 JSON 到 update 主題"""
        print(f"[{self.shadow_name}號櫃] 正在回報硬體狀態: {reported_dict}")
        
        payload = {
            "state": {
                "reported": reported_dict
            },
            "clientToken": f"pi-{int(time.time())}"
        }
        
        self.mqtt_connection.publish(
            topic=self.update_topic,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )

    def clear_desired_state(self, key_to_clear):
        """將 Desired 設為 null"""
        print(f"[{self.shadow_name}號櫃] 清除雲端指令: {key_to_clear}")
        
        payload = {
            "state": {
                "desired": {
                    key_to_clear: None
                }
            }
        }
        
        self.mqtt_connection.publish(
            topic=self.update_topic,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )
    def sync_state(self, reported_dict, clear_keys: list):
        """
        【原子化更新】同時回報狀態並清除指定的 Desired 指令。
        這能有效防止 Shadow 產生的無窮迴圈。
        """
        print(f"[{self.shadow_name}號櫃] 同步狀態：回報 {reported_dict} 並清除指令 {clear_keys}")
        
        desired_dict = {key: None for key in clear_keys}
        
        payload = {
            "state": {
                "reported": reported_dict,
                "desired": desired_dict
            },
            "clientToken": f"pi-sync-{int(time.time())}"
        }
        
        self.mqtt_connection.publish(
            topic=self.update_topic,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )