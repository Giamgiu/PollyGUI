from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                           QPushButton, QMessageBox)
import os
from ..config import CHAT_HISTORY_FOLDER

class ChatHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Chat History")
        self.setGeometry(200, 200, 300, 200)
        self.setup_ui()
        self.load_history_files()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.accept)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_selected)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(load_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    def load_history_files(self):
        for filename in os.listdir(CHAT_HISTORY_FOLDER):
            if filename.endswith('.json'):
                self.list_widget.addItem(filename)
    
    def get_selected_file(self):
        if self.list_widget.currentItem():
            return os.path.join(CHAT_HISTORY_FOLDER, self.list_widget.currentItem().text())
        return None

    def delete_selected(self):
        if self.list_widget.currentItem():
            file_path = self.get_selected_file()
            reply = QMessageBox.question(self, 'Delete Confirmation',
                                       f"Are you sure you want to delete {self.list_widget.currentItem().text()}?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.remove(file_path)
                    self.list_widget.takeItem(self.list_widget.row(self.list_widget.currentItem()))
                    QMessageBox.information(self, "Success", "File deleted successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to delete file: {str(e)}")
