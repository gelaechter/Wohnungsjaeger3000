FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
RUN mkdir -p /app/output

# These files change only when dependencies change
COPY pyproject.toml uv.lock ./

# Create the venv and install locked third-party dependencies
# without installing the local project yet
RUN uv sync --locked --no-install-project

ENV PATH="/app/.venv/bin:${PATH}"

# Install browser binaries in a stable layer
RUN patchright install --with-deps

# Application source changes only invalidate layers below this point
COPY src/ ./src/
RUN mkdir -p /app/crawl_data

# Install the local project, if your pyproject.toml defines one
RUN uv sync --locked

# Run the application every five minutes.
CMD ["bash", "-c", "while true; do uv run wohnungsjaeger3000; sleep 300; done"]