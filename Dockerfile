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

# avoid HOME/.local/share (hard to predict USER here)
# so let XDG_DATA_HOME coincide with fixed system location
# (can still be overridden by derived stages)
ENV XDG_DATA_HOME /usr/local/share
# avoid the need for an extra volume for persistent resource user db
# (i.e. XDG_CONFIG_HOME/ocrd/resources.yml)
ENV XDG_CONFIG_HOME /usr/local/share/ocrd-resources

WORKDIR /build/ocrd_pagetopdf
COPY pyproject.toml .
COPY ocrd_pagetopdf ./ocrd_pagetopdf
COPY ocrd-tool.json .
COPY requirements.txt .
COPY README.md .
COPY Makefile .
# prepackage ocrd-tool.json as ocrd-all-tool.json
RUN python -c "import json; print(json.dumps(json.load(open('ocrd-tool.json'))['tools'], indent=2))" > $(dirname $(ocrd bashlib filename))/ocrd-all-tool.json
# install everything and reduce image size
RUN make deps-ubuntu deps install \
    && rm -fr /build/ocrd_pagetopdf

WORKDIR /data
ENV DEBIAN_FRONTEND teletype
VOLUME ["/data"]

