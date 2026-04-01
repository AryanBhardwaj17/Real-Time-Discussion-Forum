FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Install uv for faster dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install shared library
COPY shared/ /tmp/shared/
RUN uv pip install --system --no-cache /tmp/shared && rm -rf /tmp/shared

# Install service dependencies
COPY content_service/pyproject.toml .
RUN uv pip install --system --no-cache $(python -c "import tomllib; f=open('pyproject.toml','rb'); deps=tomllib.load(f)['project']['dependencies']; print(' '.join(deps))")

# Copy service source
COPY content_service/ .

# Run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
