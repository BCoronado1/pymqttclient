import json
import logging
import threading
import time
import uuid
from typing import Set, Dict, Callable, Any

from paho.mqtt import client as mqtt


class MQTTClient:
    def __init__(self, client_id: str = None, host: str = "localhost", port: int = 1883,
                 subscriptions: Set[str] = frozenset(), callbacks: Set[Callable] = frozenset(),
                 reconnect_delay: float = 1.0, reconnect_msg_interval: int = 5):
        self.client_id: str = client_id
        if self.client_id is None:
            self.client_id = str(uuid.uuid4())
        self.host: str = host
        self.port: int = port
        self.callbacks: Set[Callable] = callbacks
        self.subscriptions: Set[str] = subscriptions
        self.reconnect_delay: float = reconnect_delay
        self.reconnect_msg_interval: int = reconnect_msg_interval
        if not self.subscriptions:
            self.subscriptions = {"#"}
        self.client: mqtt.Client = mqtt.Client(client_id=self.client_id,
                                               callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        threading.Thread(daemon=True, target=self.connect).start()
        logging.info(f"MQTTClient {self.client_id} configured with address {self.host}:{self.port} "
                     f"reconnect_delay: {self.reconnect_delay}s "
                     f"reconnect_msg_interval: {self.reconnect_msg_interval} "
                     f"subscriptions: {self.subscriptions}.")

    def connect(self):
        is_connected: bool = False
        num_retries = 1
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        while not is_connected:
            try:
                self.client.connect(host=self.host, port=self.port)
                self.client.loop_start()
                is_connected = True
            except Exception as e:
                if num_retries == 1 or num_retries % self.reconnect_msg_interval == 0:
                    logging.error(f"MQTTClient {self.client_id} error: {str(e)}! Retrying connection... "
                                  f"Num retries: {num_retries}.")
                num_retries += 1
                time.sleep(self.reconnect_delay)

    def publish(self, topic: str, payload: bytes):
        self.client.publish(topic=topic, payload=payload)

    def publish_dict(self, topic: str, payload_dict: Dict):
        self.publish(topic=topic, payload=json.dumps(payload_dict).encode())

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage):
        logging.debug(f"MQTTClient {self.client_id} received message. topic: {msg.topic} payload: {msg.payload}")
        for callback in self.callbacks:
            callback(topic=msg.topic, payload=msg.payload)

    def on_connect(self, client: mqtt.Client, userdata: Any, connect_flags: mqtt.ConnectFlags,
                   reason_code: mqtt.ReasonCode, properties: mqtt.Properties) -> None:
        logging.info(f"MQTTClient {self.client_id} connected to {self.host}:{self.port}.")
        for sub in self.subscriptions:
            self.client.subscribe(topic=sub)

    def on_disconnect(self, client: mqtt.Client, userdata: any, disconnect_flags: mqtt.DisconnectFlags,
                      reason_code: mqtt.ReasonCode, properties: mqtt.Properties):
        logging.info(f"MQTTClient {self.client_id} disconnected. Attempting reconnect...")
        while not self.client.is_connected():
            self.client.reconnect()
            time.sleep(1)
