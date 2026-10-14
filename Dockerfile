# Fully qualified, so engines without short-name resolution (Podman) build it as Docker does
FROM docker.io/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# --- Tool layer: install the wrapped workflow (replace for your tool) ---
RUN pip install "bilayers-algorithms @ git+https://github.com/bilayer-containers/bilayers-algorithms.git" \
    scipy scikit-image

# --- BIOMERO layer: spec parsing, OME-Zarr conversion, RO-Crate ---
# If the tool needs another Python, install this into its own environment instead,
# e.g. python3.12 -m venv /opt/biomero && /opt/biomero/bin/pip install ..., and use it in ENTRYPOINT.
COPY pyproject.toml README.md LICENSE /opt/biomero-template/
COPY src /opt/biomero-template/src
RUN pip install /opt/biomero-template

COPY config.yaml wrapper.py /app/
RUN mkdir -p /data/in /data/out
WORKDIR /app
ENTRYPOINT ["python", "/app/wrapper.py"]
