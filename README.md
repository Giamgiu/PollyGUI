# Ollama Chat GUI

This repository contains two Python-based graphical user interfaces for interacting with Ollama, a local large language model runner. The GUIs allow users to chat with Ollama models, manage chat histories, and control various aspects of the model interaction.

## Scripts

1. `chatty.py`: A feature-rich GUI built with PyQt6.
2. `light_chatty.py`: A lightweight GUI built with Tkinter, specifically designed for use on Raspberry Pi.

## Features

Both scripts offer the following features:
- Chat interface for interacting with Ollama models
- Ability to change models
- Modify system prompts
- Save and load chat histories
- Clear chat history
- Unload models from RAM
- Stop ongoing model responses

## Requirements

### For chatty.py (PyQt6 version):
- Python 3.x
- PyQt6
- requests

### For light_chatty.py (Tkinter version):
- Python 3.x
- Tkinter (comes pre-installed with Python and Raspberry Pi OS)
- requests

## Raspberry Pi Compatibility

The `light_chatty.py` script is specifically designed to run on Raspberry Pi. It uses Tkinter, which comes pre-installed with Raspberry Pi OS, making it an ideal choice for lightweight GUI applications on this platform.

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Giamgiu/PollyGUI
   cd PollyGUI
   ```

2. Install the required packages:
   For `chatty.py`:
   ```
   pip install PyQt6 requests
   ```
   For `light_chatty.py` on Raspberry Pi:
   ```
   pip install requests
   ```

## Usage

1. Make sure Ollama is running on your system.

2. Run either of the scripts:
   ```
   python chatty.py
   ```
   or for Raspberry Pi:
   ```
   python light_chatty.py
   ```

## Configuration

Both scripts use the following default configuration:
- Ollama base URL: `http://localhost:11434`
- Chat histories are saved in the user's home directory under `ollama_chat_histories`
