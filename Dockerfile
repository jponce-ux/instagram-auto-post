FROM python:3.11-slim

WORKDIR /app

# Install curl for downloading Tailwind CLI
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY .python-version .
COPY pyproject.toml .
COPY uv.lock .

RUN pip install uv

RUN uv sync --frozen --no-dev

# Download Tailwind CSS CLI standalone (v4.2.2)
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v4.2.2/tailwindcss-linux-x64 && \
    chmod +x tailwindcss-linux-x64

# Copy application
COPY . .

# Create output directory and build Tailwind CSS
RUN mkdir -p app/static/css && \
    ./tailwindcss-linux-x64 -i ./app/src/input.css -o ./app/static/css/app.css

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]