# Football Betting Prediction Bot - Backend

A FastAPI-based backend for football match predictions using machine learning.

## Architecture

This project follows **Domain-Driven Design (DDD)** and **Clean Architecture** principles:

```
src/
├── domain/          # Business logic and entities
├── application/     # Use cases and DTOs
├── infrastructure/  # External services and data sources
└── api/             # REST API layer
```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn src.api.main:app --reload --port 8000
```

## API Documentation

Once running, visit: http://localhost:8000/docs

## Environment Variables

Create a `.env` file:

```env
API_FOOTBALL_KEY=your_api_key_here
FOOTBALL_DATA_ORG_KEY=your_api_key_here
```

## Testing

```bash
pytest tests/ -v --cov=src
```

## ML Training CLI

El proyecto incluye un CLI para ejecutar el pipeline de entrenamiento ML desde la terminal.

### Comandos Disponibles

```bash
# Activar entorno virtual primero
source venv/bin/activate

# Ejecutar pipeline completo (cleanup → fetch → train → predict → top-picks)
python3 -m scripts.orchestrator_cli run-all

# Comandos individuales
python3 -m scripts.orchestrator_cli train       # Solo entrenar modelo
python3 -m scripts.orchestrator_cli predict     # Solo generar predicciones
python3 -m scripts.orchestrator_cli top-picks   # Solo generar picks sugeridos
python3 -m scripts.orchestrator_cli cleanup     # Limpiar datos antiguos
python3 -m scripts.orchestrator_cli fetch       # Obtener datos frescos
```

### Referencia Rápida

| Comando     | Descripción                               |
| ----------- | ----------------------------------------- |
| `run-all`   | Pipeline completo de ML                   |
| `train`     | Entrena el modelo con datos históricos    |
| `predict`   | Genera predicciones para partidos futuros |
| `top-picks` | Selecciona los mejores picks              |
| `cleanup`   | Elimina predicciones obsoletas            |
| `fetch`     | Descarga datos frescos de las APIs        |

> **Nota**: En macOS usar `python3` en lugar de `python`.
