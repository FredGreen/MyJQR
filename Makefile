.PHONY: dev build migrate seed web admin up down logs

up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f api worker

# 首次部署：起库 → 建表+种子
migrate:
	docker compose run --rm api python -m app.seeds

# 前端构建（产物挂载给 nginx）
web:
	cd apps/web && npm i && npm run build
admin:
	cd apps/admin && npm i && npm run build

# 本机裸跑后端（需先 pip install -r backend/requirements.txt 并把 .env 主机名改 localhost）
dev:
	cd backend && uvicorn app.main:app --reload --port 9000
worker-dev:
	cd backend && arq app.tasks.worker.WorkerSettings
