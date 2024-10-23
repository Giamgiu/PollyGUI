from PyQt6.QtCore import QThread, pyqtSignal
import json
import logging
import requests
from ..config import OLLAMA_CHAT_URL

class OllamaWorker(QThread):
    update_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, model, messages):
        super().__init__()
        self.model = model
        self.messages = messages
        self.is_running = True

    def run(self):
        try:
            logging.debug(f"Sending request to Ollama. Model: {self.model}")
            logging.debug(f"Messages: {self.messages}")
            
            response = requests.post(OLLAMA_CHAT_URL, json={
                "model": self.model,
                "messages": self.messages,
                "stream": True
            }, stream=True, timeout=500)
            
            logging.debug(f"Response status code: {response.status_code}")
            response.raise_for_status()

            for line in response.iter_lines():
                if not self.is_running:
                    break
                if line:
                    try:
                        data = json.loads(line)
                        if 'message' in data and 'content' in data['message']:
                            self.update_signal.emit(data['message']['content'])
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decode error: {e}")
                        self.error_signal.emit(f"Error decoding JSON from Ollama response: {e}")
            self.finished_signal.emit()
        except requests.exceptions.RequestException as e:
            logging.error(f"Request exception: {e}")
            self.error_signal.emit(f"Error connecting to Ollama: {str(e)}")

    def stop(self):
        self.is_running = False
