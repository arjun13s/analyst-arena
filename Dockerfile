FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY analyst_arena/ analyst_arena/

RUN pip install --no-cache-dir -e .

# Stdio transport for HUD build analysis (docker run -i); platform uses HTTP when deployed
CMD ["python", "-c", "from analyst_arena import env; env.serve(transport='stdio')"]
