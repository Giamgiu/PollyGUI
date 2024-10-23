import logging
import requests
from ..config import OLLAMA_VERSION_URL

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
