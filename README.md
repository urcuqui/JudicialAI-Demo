# JudicialAI-Demo

**Asistente Judicial con IA** — demostración educativa con Flask y Ollama para
explorar el uso responsable de inteligencia artificial en contextos
judiciales, mostrando asistencia documental, límites de delegación,
supervisión humana y riesgos como el prompt injection indirecto.

> ⚠️ Esta aplicación es una **simulación educativa**, no un sistema real de
> apoyo a decisiones judiciales. Todos los casos y datos personales usados
> son ficticios. Nunca ingrese información judicial real, confidencial o
> reservada en esta demostración.

## Qué demuestra

La aplicación presenta un caso ficticio ("Operación Horizonte") y tres
escenarios de uso de IA sobre el mismo expediente:

1. **Escenario 1 — Delegación peligrosa**: se le pide a la IA que decida
   quién tiene la razón y qué debería resolver el juez. Ilustra por qué
   delegar el razonamiento judicial a un modelo es inapropiado.
2. **Escenario 2 — Asistencia responsable**: se le pide a la IA únicamente
   que organice la información del expediente (hechos, fechas, actores,
   argumentos, evidencia, contradicciones, información no verificada), sin
   emitir juicios ni recomendaciones.
3. **Escenario 3 — Prompt injection indirecto**: el documento analizado
   contiene una instrucción oculta dirigida a la IA. Se compara el
   resultado de analizarlo sin protección frente a analizarlo con un
   system prompt que trata el documento estrictamente como datos.

También incluye un ejercicio interactivo para la audiencia
("¿Usarías IA para esto?") y un semáforo de uso responsable de IA
(verde / amarillo / rojo).

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.com) instalado y ejecutándose localmente

## Instalación

```bash
python -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configurar Ollama

Descargue un modelo (por defecto se usa `llama3.1:8b`) y arranque el
servicio:

```bash
ollama pull llama3.1:8b
ollama serve
```

Ollama debe quedar escuchando en `http://localhost:11434` (valor por
defecto).

### Cambiar el modelo

El modelo se puede configurar mediante variable de entorno sin tocar el
código:

```bash
export OLLAMA_MODEL=llama3.1:8b
```

También puede cambiarse la URL base de Ollama si el servicio corre en otro
host o puerto:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
```

## Ejecución

```bash
python app.py
```

Luego visite:

```
http://localhost:5000
```

## Despliegue con Docker

Ollama **no** se ejecuta dentro del contenedor: sigue corriendo en el host
(o en su propia infraestructura), y el contenedor de la aplicación se
conecta a él por red. Esto evita empaquetar pesos de modelos dentro de la
imagen y permite reiniciar la app sin perder el estado de Ollama.

### 1. Arrancar Ollama en el host

```bash
ollama pull llama3.1:8b
ollama serve
```

### 2. Construir y ejecutar con Docker Compose (recomendado)

```bash
docker compose up -d --build
```

Por defecto el contenedor escucha en el puerto 5050 del host (el 5000
suele estar ocupado en macOS por AirPlay Receiver) y se conecta a Ollama en
`http://host.docker.internal:11434`. Visite:

```
http://localhost:5050
```

Para usar otro modelo sin reconstruir la imagen:

```bash
OLLAMA_MODEL=gemma3:latest docker compose up -d
```

Ver logs o detener:

```bash
docker compose logs -f
docker compose down
```

### 3. Alternativa: `docker build` / `docker run` manual

```bash
docker build -t judicial-ai-demo:latest .

docker run -d \
  --name judicial-ai-demo \
  -p 5050:5000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e OLLAMA_MODEL=llama3.1:8b \
  --add-host=host.docker.internal:host-gateway \
  judicial-ai-demo:latest
```

`--add-host=host.docker.internal:host-gateway` es necesario en Linux; en
Docker Desktop (macOS/Windows) `host.docker.internal` ya resuelve de forma
nativa, pero incluir la bandera no causa ningún problema.

### Notas de la imagen

- Basada en `python:3.11-slim`, ejecuta la app como usuario sin privilegios
  (`app`), nunca como root.
- Sirve la aplicación con `gunicorn` (no el servidor de desarrollo de
  Flask), con `--timeout 120` porque las consultas a modelos locales
  pueden tardar más que el timeout por defecto.
- Incluye un `HEALTHCHECK` que verifica `GET /api/case`.
- `.dockerignore` excluye el entorno virtual, `.git` y archivos temporales
  para mantener la imagen ligera.

## Modo Presentación

El botón **Modo Presentación**, en la parte superior de la aplicación,
aumenta el tamaño de la tipografía y de los botones, y oculta controles
secundarios, para facilitar la demostración proyectada en un auditorio.
Toda la demostración puede realizarse usando únicamente el mouse.

## Reiniciar la demostración

El botón **Reiniciar demostración** restaura el estado inicial de la
aplicación. Cada consulta a la IA es independiente (sin historial de
conversación persistente), de modo que la demostración es reproducible en
cada ejecución en vivo.

## Arquitectura

```
judicial-ai-demo/
│
├── app.py                  # Rutas Flask y validación de respuestas
├── config.py                # Configuración (modelo, timeouts, límites)
├── requirements.txt
├── README.md
├── Dockerfile               # Imagen de la aplicación Flask (sin Ollama)
├── docker-compose.yml       # Orquestación local, conecta al Ollama del host
├── .dockerignore
│
├── services/
│   └── ollama_service.py   # Único punto de comunicación con Ollama
│
├── demo/
│   ├── cases.py            # Caso ficticio (versión limpia y con injection)
│   └── prompts.py          # System prompts y prompts de usuario por escenario
│
├── templates/
│   ├── base.html
│   └── index.html
│
└── static/
    ├── css/style.css
    └── js/app.js
```

## Seguridad y límites de diseño

- El navegador **nunca** puede enviar system prompts propios: todos los
  prompts que definen el comportamiento del modelo están fijados en el
  backend (`demo/prompts.py`).
- El backend es el único componente que habla con la API de Ollama; el
  frontend solo llama a endpoints propios de Flask.
- No se ejecuta ni evalúa ninguna salida del modelo (no `eval`, no `exec`,
  sin ejecución de shell, sin rutas de archivo arbitrarias).
- Las respuestas estructuradas (JSON) se validan en el servidor antes de
  renderizarse; si el parseo falla, se muestra el texto sin procesar como
  respaldo.
- El tamaño máximo de solicitud está limitado (`MAX_CONTENT_LENGTH`).
- El frontend inserta la salida del modelo mediante `textContent` (nunca
  `innerHTML`), evitando la inyección de HTML/JS en el navegador.
- No se usa base de datos ni se almacenan conversaciones de forma
  permanente. El ejercicio interactivo de audiencia guarda su estado solo
  en memoria del navegador (JavaScript), sin recolectar información
  personal.

## API

| Método | Ruta                        | Descripción                                              |
|--------|-----------------------------|-----------------------------------------------------------|
| GET    | `/`                         | Página principal                                          |
| GET    | `/api/case`                 | Devuelve el expediente ficticio (con y sin injection)     |
| POST   | `/api/analyze/dangerous`    | Escenario 1 — delegación peligrosa                        |
| POST   | `/api/analyze/responsible`  | Escenario 2 — asistencia responsable (JSON estructurado)   |
| POST   | `/api/analyze/injection`    | Escenario 3 — análisis sin protección contra injection     |
| POST   | `/api/analyze/protected`    | Escenario 3 — análisis con protección contra injection     |
