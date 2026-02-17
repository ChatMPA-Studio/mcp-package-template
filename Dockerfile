# =============================================================================
# Stage 1: Builder — install dependencies into a prefix directory
# =============================================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install build tools
RUN pip install --no-cache-dir setuptools wheel

# Copy only dependency metadata first (layer caching)
COPY pyproject.toml ./

# Create stub packages so setuptools can resolve the install.
# --force-reinstall ensures transitive deps (e.g., packaging) get installed
# into the --prefix path even if already present in the builder environment.
# Without this, multi-stage builds silently drop transitive dependencies.
RUN mkdir -p mcp_server mcp_server/tools mcp_server/skills \
             mcp_server/config mcp_server/security mcp_server/metadata \
             mcp_server/resources && \
    touch mcp_server/__init__.py mcp_server/tools/__init__.py \
          mcp_server/skills/__init__.py mcp_server/config/__init__.py \
          mcp_server/security/__init__.py mcp_server/metadata/__init__.py \
          mcp_server/resources/__init__.py && \
    pip install --no-cache-dir --force-reinstall --prefix=/install . && \
    rm -rf mcp_server

# =============================================================================
# Stage 2: Runtime — lean production image
# =============================================================================
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy pre-built dependencies from builder
COPY --from=builder /install /usr/local

# Copy application source and install package (deps already cached)
COPY pyproject.toml ./
COPY mcp_server/ mcp_server/
COPY metadata/ metadata/
RUN pip install --no-cache-dir --no-deps .

# Health check script
COPY healthcheck.py ./

# Run as non-root for security
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid mcp --shell /bin/false mcp && \
    chown -R mcp:mcp /app
USER mcp

# Default port — override with PORT env var
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "healthcheck.py"]

CMD ["python", "-m", "mcp_server"]
