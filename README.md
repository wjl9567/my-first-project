# 医院设备扫码登记 - FastAPI 骨架

Quick start:
1. Copy `.env.example` to `.env` and adjust DATABASE_URL and MinIO settings.
2. Start services:
   ```bash
   docker-compose up --build
   ```
3. Open API docs: http://localhost:8000/docs
4. Frontend prototype: http://localhost:8000/static/index.html

Temporary admin for testing (do NOT use in production): admin / abc123

Notes:
- Uses FastAPI + SQLModel + PostgreSQL + MinIO (S3 compatible)
- Patient IDs are NOT stored per project settings.
