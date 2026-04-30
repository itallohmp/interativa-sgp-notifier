FROM python:3.11-slim

# Evita arquivos .pyc e força logs sem buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 

# Instala Poetry corretamente
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copia apenas os arquivos de dependência primeiro (melhora cache)
COPY pyproject.toml poetry.lock* /app/

# Configura Poetry para instalar dependências no sistema (sem virtualenv)
RUN poetry config virtualenvs.create false

# Instala dependências
RUN poetry install --no-interaction --no-ansi

# Copia o restante do código
COPY . /app

# Comando para rodar FastAPI com Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
