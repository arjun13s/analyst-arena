FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY analyst_arena/ analyst_arena/

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["python", "-c", "from analyst_arena import env; env.serve(host='0.0.0.0', port=8000)"]
