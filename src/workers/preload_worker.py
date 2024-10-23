from PyQt6.QtCore import QObject, pyqtSignal
import requests
from ..config import OLLAMA_CHAT_URL

class PreloadWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.is_running = True

    def run(self):
        try:
            response = requests.post(OLLAMA_CHAT_URL, json={
                "model": self.model
            }, timeout=60)
            response.raise_for_status()
            if self.is_running:
                self.finished.emit()
        except requests.exceptions.RequestException as e:
            if self.is_running:
                self.error.emit(str(e))

    def stop(self):
        self.is_running = False
