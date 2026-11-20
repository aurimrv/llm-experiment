FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    PROTEUMIMHOME=/work/tools/ProteumIM64/bin \
    PATH="/opt/venv/bin:/work/tools/ProteumIM64/bin:${PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        gcc \
        clang \
        libc6-dev \
        make \
        gawk \
        bash \
        ca-certificates \
        tcl \
        tk \
        xterm \
        xauth \
        x11-utils \
        indent \
        less \
        fontconfig \
        fonts-dejavu-core \
        xfonts-base \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
COPY scripts/requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/proteumim-wrap.tcl /usr/local/lib/proteumim-wrap.tcl
RUN chmod 755 /usr/local/bin/entrypoint.sh

WORKDIR /work
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["bash"]
