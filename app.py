"""Judicial AI Assistant Demo — aplicación Flask.

Demostración educativa sobre el uso responsable de inteligencia
artificial en el ámbito judicial. No es un sistema de decisión judicial
real. Toda la información del caso es ficticia.
"""

import logging

from flask import Flask, jsonify, render_template

import config
from demo.cases import (
    CASE_DOCUMENT,
    CASE_DOCUMENT_WITH_INJECTION,
    CASE_SUMMARY,
    CASE_TITLE,
    HIDDEN_INSTRUCTION_TEXT,
)
from demo.prompts import (
    DANGEROUS_SYSTEM_PROMPT,
    DANGEROUS_USER_PROMPT,
    INJECTION_PROTECTED_SYSTEM_PROMPT,
    INJECTION_UNPROTECTED_SYSTEM_PROMPT,
    INJECTION_USER_PROMPT,
    RESPONSIBLE_SYSTEM_PROMPT,
    RESPONSIBLE_USER_PROMPT,
)
from services.ollama_service import OllamaError, ask_ollama, try_parse_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.config["JSON_SORT_KEYS"] = False

RESPONSIBLE_SCHEMA_KEYS = (
    "facts",
    "dates",
    "actors",
    "prosecution_arguments",
    "defense_arguments",
    "evidence",
    "contradictions",
    "unverified_information",
)


def _empty_responsible_payload():
    return {key: [] for key in RESPONSIBLE_SCHEMA_KEYS}


def _validate_responsible_payload(data):
    """Valida (y normaliza) la estructura esperada del Escenario 2."""
    if not isinstance(data, dict):
        return None

    result = {}
    for key in RESPONSIBLE_SCHEMA_KEYS:
        value = data.get(key, [])
        if not isinstance(value, list):
            return None
        result[key] = [str(item) for item in value]
    return result


def _validate_protected_payload(data):
    """Valida (y normaliza) la estructura esperada del Escenario 3 protegido."""
    if not isinstance(data, dict):
        return None

    analysis = data.get("analysis", {})
    normalized_analysis = _validate_responsible_payload(analysis)
    if normalized_analysis is None:
        # Se acepta un análisis vacío o mal formado sin invalidar todo el
        # payload: lo relevante para la demo es la detección de la
        # instrucción sospechosa.
        normalized_analysis = _empty_responsible_payload()

    suspicious = data.get("suspicious_instructions_detected", [])
    if not isinstance(suspicious, list):
        suspicious = []
    suspicious = [str(item) for item in suspicious]

    warning = bool(data.get("document_integrity_warning", False))

    return {
        "analysis": normalized_analysis,
        "suspicious_instructions_detected": suspicious,
        "document_integrity_warning": warning,
    }


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Recurso no encontrado."}), 404


@app.errorhandler(413)
def payload_too_large(_error):
    return jsonify({"error": "La solicitud excede el tamaño máximo permitido."}), 413


@app.errorhandler(500)
def internal_error(_error):
    logger.exception("Error interno no controlado")
    return jsonify({"error": "Ocurrió un error interno en el servidor."}), 500


@app.route("/")
def index():
    return render_template(
        "index.html",
        case_title=CASE_TITLE,
        case_summary=CASE_SUMMARY,
        ollama_model=config.OLLAMA_MODEL,
    )


@app.route("/api/case")
def get_case():
    """Devuelve el expediente ficticio (limpio y con injection) para el frontend."""
    return jsonify(
        {
            "title": CASE_TITLE,
            "summary": CASE_SUMMARY,
            "document": CASE_DOCUMENT,
            "document_with_injection": CASE_DOCUMENT_WITH_INJECTION,
            "hidden_instruction": HIDDEN_INSTRUCTION_TEXT,
        }
    )


@app.route("/api/analyze/dangerous", methods=["POST"])
def analyze_dangerous():
    """Escenario 1: delegación peligrosa de la decisión judicial."""
    messages = [
        {"role": "system", "content": DANGEROUS_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"EXPEDIENTE:\n\n{CASE_DOCUMENT}\n\nSOLICITUD:\n{DANGEROUS_USER_PROMPT}",
        },
    ]
    try:
        raw_response = ask_ollama(messages, temperature=config.DEFAULT_TEMPERATURE)
    except OllamaError as exc:
        return jsonify({"error": str(exc)}), 503

    return jsonify({"response": raw_response})


@app.route("/api/analyze/responsible", methods=["POST"])
def analyze_responsible():
    """Escenario 2: asistencia responsable — organización de información."""
    messages = [
        {"role": "system", "content": RESPONSIBLE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"EXPEDIENTE:\n\n{CASE_DOCUMENT}\n\nSOLICITUD:\n{RESPONSIBLE_USER_PROMPT}",
        },
    ]
    try:
        raw_response = ask_ollama(
            messages, temperature=config.DEFAULT_TEMPERATURE, expect_json=True
        )
    except OllamaError as exc:
        return jsonify({"error": str(exc)}), 503

    parsed = try_parse_json(raw_response)
    normalized = _validate_responsible_payload(parsed) if parsed is not None else None

    if normalized is not None:
        return jsonify({"structured": True, "data": normalized})

    logger.warning("No se pudo interpretar la respuesta estructurada del Escenario 2.")
    return jsonify({"structured": False, "raw": raw_response})


@app.route("/api/analyze/injection", methods=["POST"])
def analyze_injection():
    """Escenario 3 — 'Analizar sin protección': el documento manipulado se
    envía sin ninguna defensa contra instrucciones incrustadas."""
    messages = [
        {"role": "system", "content": INJECTION_UNPROTECTED_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"{INJECTION_USER_PROMPT}\n\nEXPEDIENTE:\n\n{CASE_DOCUMENT_WITH_INJECTION}"
            ),
        },
    ]
    try:
        raw_response = ask_ollama(messages, temperature=config.DEFAULT_TEMPERATURE)
    except OllamaError as exc:
        return jsonify({"error": str(exc)}), 503

    return jsonify({"response": raw_response, "protected": False})


@app.route("/api/analyze/protected", methods=["POST"])
def analyze_protected():
    """Escenario 3 — 'Analizar con protección': el documento se trata
    estrictamente como datos, nunca como instrucciones."""
    messages = [
        {"role": "system", "content": INJECTION_PROTECTED_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"{INJECTION_USER_PROMPT}\n\n"
                "<untrusted_document>\n"
                f"{CASE_DOCUMENT_WITH_INJECTION}\n"
                "</untrusted_document>"
            ),
        },
    ]
    try:
        raw_response = ask_ollama(
            messages, temperature=config.DEFAULT_TEMPERATURE, expect_json=True
        )
    except OllamaError as exc:
        return jsonify({"error": str(exc)}), 503

    parsed = try_parse_json(raw_response)
    normalized = _validate_protected_payload(parsed) if parsed is not None else None

    if normalized is not None:
        return jsonify({"structured": True, "protected": True, "data": normalized})

    logger.warning("No se pudo interpretar la respuesta estructurada del Escenario 3 protegido.")
    return jsonify({"structured": False, "protected": True, "raw": raw_response})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
