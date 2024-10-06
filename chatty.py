import sys
import json
import logging
import requests
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QInputDialog, QFileDialog,
    QMessageBox, QListWidget, QDialog, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QObject, QTimer
from PyQt6.QtGui import QTextCursor, QFont, QColor

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_VERSION_URL = f"{OLLAMA_BASE_URL}/api/version"

# Create a folder for saving chat histories
CHAT_HISTORY_FOLDER = os.path.join(os.path.expanduser("~"), "ollama_chat_histories")
os.makedirs(CHAT_HISTORY_FOLDER, exist_ok=True)

def check_ollama_version():
    try:
        response = requests.get(OLLAMA_VERSION_URL)
        response.raise_for_status()
        version = response.json().get('version', 'unknown')
        logging.info(f"Ollama version: {version}")
        return version
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to get Ollama version: {e}")
        return None

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
            }, stream=True, timeout=300)
            
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


class ChatHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Chat History")
        self.setGeometry(200, 200, 300, 200)
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(load_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.load_history_files()
    
    def load_history_files(self):
        for filename in os.listdir(CHAT_HISTORY_FOLDER):
            if filename.endswith('.json'):
                self.list_widget.addItem(filename)
    
    def get_selected_file(self):
        if self.list_widget.currentItem():
            return os.path.join(CHAT_HISTORY_FOLDER, self.list_widget.currentItem().text())
        return None

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

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama Chat GUI")
        self.setGeometry(100, 100, 800, 600)

        self.model = "hubble"
        self.system_prompt = "You are a helpful AI assistant."
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.current_message = ""
        self.is_ready = False

        self.setup_ui()
        self.status_label = QLabel("Initializing...")
        self.statusBar().addPermanentWidget(self.status_label)

        self.thread = None
        self.worker = None

        # Use a timer to start the Ollama check and preload after the event loop starts
        QTimer.singleShot(0, self.initialize_ollama)

    def initialize_ollama(self):
        self.check_ollama()
        if self.is_ready:
            self.preload_model()

    def preload_model(self):
        self.status_label.setText("Preloading model...")
        self.chat_display.append("Preloading model. Please wait...")
        
        self.thread = QThread()
        self.worker = PreloadWorker(self.model)
        self.worker.moveToThread(self.thread)
        
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_preload_finished)
        self.worker.error.connect(self.on_preload_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

    def on_preload_finished(self):
        self.chat_display.append(f"Model {self.model} preloaded successfully.")
        self.set_ready_state(True)

    def on_preload_error(self, error):
        error_msg = f"Error preloading model: {error}"
        self.chat_display.append(error_msg)
        self.show_error(error_msg)
        self.set_ready_state(False)

    def check_ollama(self):
        version = check_ollama_version()
        if version:
            self.chat_display.append(f"Connected to Ollama version: {version}\n")
            self.is_ready = True
        else:
            self.chat_display.append("Failed to connect to Ollama. Please make sure it's running.\n")
            self.set_ready_state(False)
            QMessageBox.warning(self, "Connection Error", "Failed to connect to Ollama. Please make sure it's running.")

    def closeEvent(self, event):
        self.stop_model()
        if self.worker:
            self.worker.stop()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(5000)  # Wait up to 5 seconds
            if self.thread.isRunning():
                self.thread.terminate()
        event.accept()


    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        
        # Set font to Ubuntu and increase size
        font = QFont("Ubuntu", 16)
        self.chat_display.setFont(font)
        
        layout.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Ubuntu", 14))  # Increase input text size
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)

        stop_model_button = QPushButton("Stop Model")
        stop_model_button.clicked.connect(self.stop_model)
        input_layout.addWidget(stop_model_button)

        layout.addLayout(input_layout)
        button_layout = QHBoxLayout()
        
        modify_system_prompt_button = QPushButton("Modify System Prompt")
        modify_system_prompt_button.clicked.connect(self.modify_system_prompt)
        button_layout.addWidget(modify_system_prompt_button)

        save_history_button = QPushButton("Save History")
        save_history_button.clicked.connect(self.save_history)
        button_layout.addWidget(save_history_button)

        load_history_button = QPushButton("Load History")
        load_history_button.clicked.connect(self.load_history)
        button_layout.addWidget(load_history_button)

        change_model_button = QPushButton("Change Model")
        change_model_button.clicked.connect(self.change_model)
        button_layout.addWidget(change_model_button)

        # Add Clear History button
        clear_history_button = QPushButton("Clear History")
        clear_history_button.clicked.connect(self.clear_history)
        button_layout.addWidget(clear_history_button)

        layout.addLayout(button_layout)

    def send_message(self):
        if not self.is_ready:
            return  # Ignore send attempts when not ready

        user_message = self.input_field.text().strip()
        if not user_message:
            return

        self.set_ready_state(False)  # Disable input when sending message

        

        self.chat_display.setTextColor(QColor("gray"))
        self.chat_display.append(f"You: {user_message}")
        self.chat_display.setTextColor(QColor("black"))
        self.input_field.clear()
        self.messages.append({"role": "user", "content": user_message})

        logging.debug(f"Sending message: {user_message}")
        self.worker = OllamaWorker(self.model, self.messages)
        self.worker.update_signal.connect(self.update_chat_display)
        self.worker.error_signal.connect(self.show_error)
        self.worker.finished_signal.connect(self.on_response_finished)
        self.worker.start()
        self.current_message = ""
        self.chat_display.append("")
        self.status_label.setText("Processing...")

    def update_chat_display(self, token):
        self.current_message += token
        self.chat_display.setTextColor(QColor("black"))
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(token)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

        # Scroll to the bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


    def on_response_finished(self):
          # Add an extra newline after the assistant's response
        self.messages.append({"role": "assistant", "content": self.current_message.strip()})
        self.current_message = ""
        logging.debug("Response finished")
        self.set_ready_state(True)  # Re-enable input when response is finished

    def set_ready_state(self, is_ready):
            self.is_ready = is_ready
            self.input_field.setEnabled(True)
            self.send_button.setEnabled(is_ready)
            self.status_label.setText("Ready" if is_ready else "Processing...")

    def modify_system_prompt(self):
        new_prompt, ok = QInputDialog.getMultiLineText(self, "Modify System Prompt", 
                                                       "Enter new system prompt:", self.system_prompt)
        if ok:
            self.system_prompt = new_prompt
            self.messages = [{"role": "system", "content": self.system_prompt}] + [msg for msg in self.messages if msg['role'] != 'system']
            self.chat_display.setTextColor(QColor("blue"))
            self.chat_display.append(f"\nSystem prompt updated to: {self.system_prompt}\n")
            self.chat_display.setTextColor(QColor("black"))
            logging.debug(f"System prompt updated: {self.system_prompt}")

    def save_history(self):
        name, ok = QInputDialog.getText(self, "Save Chat History", "Enter a name for this chat history:")
        if ok and name:
            filename = os.path.join(CHAT_HISTORY_FOLDER, f"{name}.json")
            with open(filename, 'w') as f:
                json.dump({
                    "messages": self.messages,
                    "model": self.model
                }, f)
            self.chat_display.setTextColor(QColor("green"))
            self.chat_display.append(f"\nChat history saved to {filename}\n")
            self.chat_display.setTextColor(QColor("black"))
            logging.debug(f"Chat history saved to {filename}")

    def load_history(self):
        dialog = ChatHistoryDialog(self)
        if dialog.exec():
            filename = dialog.get_selected_file()
            if filename:
                with open(filename, 'r') as f:
                    data = json.load(f)
                    self.messages = data.get("messages", [])
                    self.model = data.get("model", self.model)
                self.chat_display.clear()
                for msg in self.messages:
                    if msg['role'] == 'system':
                        self.system_prompt = msg['content']
                    elif msg['role'] == 'user':
                        self.chat_display.setTextColor(QColor("gray"))
                        self.chat_display.append(f"You: {msg['content']}\n")
                        self.chat_display.setTextColor(QColor("black"))
                    elif msg['role'] == 'assistant':
                        self.chat_display.append(f"{msg['content']}\n")
                self.chat_display.setTextColor(QColor("green"))
                self.chat_display.append(f"\nChat history loaded from {filename}\n")
                self.chat_display.append(f"System prompt: {self.system_prompt}\n")
                self.chat_display.append(f"Model: {self.model}\n")
                self.chat_display.setTextColor(QColor("black"))
                logging.debug(f"Chat history loaded from {filename}")

    def clear_history(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.chat_display.clear()
        self.chat_display.setTextColor(QColor("red"))
        self.chat_display.append("Chat history cleared.\n")
        self.chat_display.setTextColor(QColor("black"))
        logging.debug("Chat history cleared")

    def change_model(self):
        new_model, ok = QInputDialog.getText(self, "Change Model", "Enter new model name:")
        if ok and new_model:
            old_model = self.model
            self.model = new_model
            self.chat_display.setTextColor(QColor("blue"))
            self.chat_display.append(f"\nModel changed from {old_model} to {new_model}\n")
            self.chat_display.setTextColor(QColor("black"))
            logging.debug(f"Model changed from {old_model} to {new_model}")


    
    def stop_model(self):
        self.chat_display.setTextColor(QColor("red"))
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()            
            self.chat_display.append(f"\nStopped model: {self.model}\n")
            self.set_ready_state(True)  # Re-enable input when stopping the model
            logging.debug(f"Stopped model: {self.model}")
        else:
            self.chat_display.append("\nNo active model to stop.\n")

    

    def show_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)
        self.chat_display.append(f"\nError: {error_message}\n")
        logging.error(f"Error displayed: {error_message}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
