import sys
import logging
from PyQt6.QtWidgets import QApplication
from .gui.chat_window import ChatWindow

def main():
    logging.basicConfig(level=logging.DEBUG, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()