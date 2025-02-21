ARG DOCKER_BASE_IMAGE
FROM $DOCKER_BASE_IMAGE

ARG VCS_REF
ARG BUILD_DATE
LABEL \
    maintainer="https://ocr-d.de/kontakt" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.vcs-url="https://github.com/UB-Mannheim/ocrd_pagetopdf" \
    org.label-schema.build-date=$BUILD_DATE

ENV DEBIAN_FRONTEND noninteractive

WORKDIR /build/ocrd_pagetopdf
COPY setup.py .
COPY ocrd_pagetopdf ./ocrd_pagetopdf
COPY ocrd-tool.json .
COPY requirements.txt .
COPY README.md .
COPY Makefile .
RUN make deps-ubuntu deps install \
    && rm -fr /build/ocrd_pagetopdf

WORKDIR /data
ENV DEBIAN_FRONTEND teletype
VOLUME ["/data"]

