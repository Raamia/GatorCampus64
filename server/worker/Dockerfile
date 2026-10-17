# Gatorize Me GPU worker: Python deps + Blender's runtime libraries only. Blender and the repo
# (tools/blender, tools/vendor, tools/blender-scripts and this worker's code) are mounted
# read-only from the host (server/deploy/provision_gpu.sh installs them), see docker-compose.yml.
FROM nvidia/cuda:12.6.3-base-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
    HOME=/tmp/home

# libs from provision_gpu.sh (Blender 4.5 headless + EGL); the NVIDIA runtime injects the
# driver's libEGL_nvidia / glvnd vendor file when the "graphics" capability is requested
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends python3 python3-venv ca-certificates \
        libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libx11-6 libgl1 libegl1 \
        libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir -q -r /tmp/requirements.txt

RUN useradd -m -u 1001 sgl && mkdir -p /tmp/home /work && chown sgl /tmp/home /work
USER sgl
ENV SGL_REPO=/opt/sgl64 BLENDER=/opt/blender-4.5.3/blender WORK_ROOT=/work
WORKDIR /opt/sgl64/server/worker
CMD ["/venv/bin/python", "/opt/sgl64/server/worker/worker.py"]
