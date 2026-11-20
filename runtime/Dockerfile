FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git tmux asciinema build-essential ca-certificates && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir numpy==2.3.5 scipy==1.16.3 cryptography==44.0.3
ENV PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
