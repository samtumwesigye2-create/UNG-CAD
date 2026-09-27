FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libopengl0 libgl1 libegl1 libglu1-mesa libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0 libxrender1 libxext6 libsm6 libglib2.0-0 libfontconfig1 libdbus-1-3 ca-certificates wget && rm -rf /var/lib/apt/lists/*
COPY ung-cad-3d/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ung-cad-3d/ .
# Build from repository root so the shared CAD kernel is inside the Docker context.
COPY cad_core /cad_core
COPY ung_shared /ung_shared
COPY ung_geometry /ung_geometry
ENV PYTHONPATH=/
RUN python tests/analytic_build_gate.py
RUN pytest -q tests/test_draco_manufacturing_api.py
ENV QT_QPA_PLATFORM=offscreen
CMD ["sh","-c","python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
