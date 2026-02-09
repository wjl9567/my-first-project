# 医院设备扫码登记系统 - 生产镜像
# Python 3.10 + Poetry 安装依赖，单进程 Uvicorn
FROM python:3.10-slim

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
# 应用代码在 /app，backend 包从 /app 导入
ENV PYTHONPATH=/app
# 生产环境（用于强制校验 JWT_SECRET）
ENV ENVIRONMENT=production

WORKDIR /app

# 安装系统依赖（可选，按需取消注释）
# RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# 安装 Poetry
RUN pip install --no-cache-dir poetry

# 复制项目（含 backend/、readme 等）
COPY backend/pyproject.toml backend/poetry.lock ./backend/
COPY backend/ ./backend/
COPY readme.md ./

# 在 backend 目录用 Poetry 安装依赖（不创建 venv，直接装到系统 Python）
WORKDIR /app/backend
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

WORKDIR /app

# 非 root 运行（可选，按需取消注释）
# RUN useradd -m -u 1000 appuser && chown -R appuser /app
# USER appuser

EXPOSE 8000

# 单进程；多 worker 可在 CMD 中改为 uvicorn ... --workers 2
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
