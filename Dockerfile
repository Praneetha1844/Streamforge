# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
RUN useradd --system --create-home --uid 10001 app
WORKDIR /app
COPY --from=build /src/dist/*.whl /tmp/
RUN pip install "$(ls /tmp/*.whl)[postgres,pubsub]" && rm -f /tmp/*.whl
COPY schemas ./schemas
COPY quality ./quality
COPY migrations ./migrations
USER app
EXPOSE 8000 9100
ENTRYPOINT ["streamforge"]
CMD ["serve"]
