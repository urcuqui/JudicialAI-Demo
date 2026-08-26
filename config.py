"""Configuración central de la aplicación de demostración."""

import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

# Tiempo máximo (segundos) para esperar respuesta de Ollama antes de fallar
# de forma controlada. Una demo en vivo no puede quedarse colgada.
OLLAMA_CONNECT_TIMEOUT = 5
OLLAMA_READ_TIMEOUT = 90

# Temperatura baja para respuestas reproducibles durante la demostración en vivo.
DEFAULT_TEMPERATURE = 0.2

# Límite de tamaño de payload aceptado por Flask (protección básica).
MAX_CONTENT_LENGTH = 256 * 1024  # 256 KB

SECRET_KEY = os.environ.get("SECRET_KEY", "judicial-ai-demo-dev-key")
