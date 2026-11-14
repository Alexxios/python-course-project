FROM python:3.15-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Build from the workspace root to include shared libraries and uv.lock.
COPY . .
# Install locked runtime dependencies as non-editable packages.
RUN uv sync --locked --package app --no-dev --no-editable
EXPOSE 80
# Start the ASGI app using the environment installed during the build.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
