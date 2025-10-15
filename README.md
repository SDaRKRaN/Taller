# Taller (Proyecto Python)

Código del proyecto Python. Repo limpio sin `venv/` ni binarios.

## Requisitos rápidos
```bash
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Desarrollo
- Ejecuta la app: `python app.py` (o el entrypoint que uses: `python main.py`).
- Añade dependencias con `pip install paquete` y luego `pip freeze > requirements.txt`.

## Buenas prácticas
- No subir `venv/`, `.db`, `.xlsx`, `.exe`, `.dll`, etc.
- Variables sensibles en `.env` (no versionado). Mantén `./.env.example` como plantilla.
