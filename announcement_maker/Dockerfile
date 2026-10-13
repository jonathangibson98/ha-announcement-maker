# Supervisor passes BUILD_FROM; the default keeps it buildable by hand too.
ARG BUILD_FROM=ghcr.io/home-assistant/base:latest
FROM ${BUILD_FROM}
RUN apk add --no-cache python3 py3-yaml
WORKDIR /app
COPY run.sh server.py /app/
COPY www /app/www
RUN chmod a+x /app/run.sh
CMD ["/app/run.sh"]
