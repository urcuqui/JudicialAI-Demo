"""Servicio reutilizable para hablar con una instancia local de Ollama.

Este módulo es el único punto del backend que se comunica con Ollama.
El navegador nunca tiene acceso directo a la API de Ollama: todo pasa
por los endpoints de Flask, que son quienes deciden el system prompt.
"""

import json
import logging

import requests

from config import (
    DEFAULT_TEMPERATURE,
    OLLAMA_BASE_URL,
    OLLAMA_CONNECT_TIMEOUT,
    OLLAMA_MODEL,
    OLLAMA_READ_TIMEOUT,
)

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Error controlado al comunicarse con Ollama."""


def ask_ollama(messages, temperature=DEFAULT_TEMPERATURE, model=None, expect_json=False):
    """Envía una conversación a Ollama y devuelve el texto de la respuesta.

    Cada llamada es independiente (sin historial persistente) para que
    cada escenario de la demo empiece con un contexto limpio y
    reproducible, tal como exige una demostración en vivo.

    Args:
        messages: lista de dicts {"role": ..., "content": ...}
        temperature: temperatura de muestreo (baja por defecto)
        model: sobrescribe el modelo configurado por entorno
        expect_json: si es True, se le pide a Ollama que fuerce salida JSON

    Returns:
        str: contenido de la respuesta del modelo

    Raises:
        OllamaError: si Ollama no está disponible o responde con error
    """
    payload = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if expect_json:
        payload["format"] = "json"

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=(OLLAMA_CONNECT_TIMEOUT, OLLAMA_READ_TIMEOUT),
        )
    except requests.exceptions.ConnectTimeout as exc:
        raise OllamaError(
            "No se pudo conectar con Ollama. Verifique que el servicio "
            f"esté activo en {OLLAMA_BASE_URL} (comando: 'ollama serve')."
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            "No se pudo conectar con Ollama. Verifique que el servicio "
            f"esté activo en {OLLAMA_BASE_URL} (comando: 'ollama serve')."
        ) from exc
    except requests.exceptions.ReadTimeout as exc:
        raise OllamaError(
            "Ollama tardó demasiado en responder. Intente nuevamente o "
            "utilice un modelo más pequeño para la demostración."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Error inesperado al comunicarse con Ollama: {exc}") from exc

    if response.status_code != 200:
        logger.error("Ollama respondió %s: %s", response.status_code, response.text[:500])
        raise OllamaError(
            f"Ollama respondió con un error (HTTP {response.status_code}). "
            "Verifique que el modelo configurado esté descargado (ollama pull)."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaError("Ollama devolvió una respuesta que no es JSON válido.") from exc

    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        raise OllamaError("Ollama devolvió una respuesta vacía.")

    return content


def try_parse_json(text):
    """Intenta extraer un objeto JSON de la respuesta del modelo.

    Los modelos locales a veces envuelven el JSON en texto adicional o
    en bloques de código markdown, así que se hace un intento razonable
    de extraerlo antes de rendirse.

    Returns:
        dict | None: el objeto parseado, o None si no fue posible.
    """
    if not text:
        return None

    text = text.strip()

    # Quitar cercas de bloque de código si el modelo las añadió.
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except (ValueError, json.JSONDecodeError):
            return None

    return None
