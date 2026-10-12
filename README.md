# MyJQR —— AI 写作平台（Web 版）

对标焦圈儿的开源实现：模板化 AI 写作 + 联网搜索 + AI 率检测 + 焦耳计费。
技术栈：**FastAPI + ARQ + Redis + MySQL + Milvus(预留) ｜ Vue3 双端 ｜ Docker Compose**

```
MyJQR/
├── docker-compose.yml        # nginx + api + worker(arq) + mysql + redis [+ milvus profile]
├── .env.example              # 复制为 .env 填写 API Key
├── backend/                  # FastAPI 后端（app/ 下分 core/models/services/pipelines/tasks/api）
├── apps/web/                 # 用户端（模板市场/创作SSE/作品/焦耳）
├── apps/admin/               # 管理后台（看板/模板/兑换码/审核）
└── deploy/nginx/nginx.conf   # 静态 + /api 反代（SSE 已关缓冲）
```

## 快速启动（有 Docker 的机器）

```bash
cp .env.example .env          # 填入 DEEPSEEK_API_KEY（必填）、ZHIPU_API_KEY、BOCHA_API_KEY（可选）
docker compose up -d --build  # 起 nginx/api/worker/mysql/redis
docker compose run --rm api python -m app.seeds   # 建表 + 15分类/10模板/管理员
# 前端（本机构建产物挂给 nginx）
cd apps/web && npm i && npm run build && cd ../..
cd apps/admin && npm i && npm run build && cd ../..
# 访问：http://服务器IP/（用户端）  http://服务器IP/admin/（管理后台 admin / admin123456）
```

## 本机开发（无 Docker）

需要自备 MySQL 8 与 Redis，`.env` 中主机名改 `localhost`：

```bash
cd backend
pip install -r requirements.txt
python -m app.seeds                                # 建表+种子
uvicorn app.main:app --reload --port 9000          # API :9000
arq app.tasks.worker.WorkerSettings                # ARQ worker（另开终端）
cd ../apps/web && npm i && npm run dev             # 用户端 :8080（/api 已代理）
cd ../admin && npm i && npm run dev                # 后台 :8081
```

## 已实现功能（MVP 骨架）

- ✅ 邮箱注册/登录（JWT RS256 自动生成密钥对）、新人赠 100J
- ✅ 模板市场：15 分类 / 10 模板（含真实提示词）/ 推荐 / 分类浏览 / 收藏
- ✅ 一键生成：敏感词预检 → 焦耳冻结 → ARQ 任务 → 博查搜索(可选) → DeepSeek/GLM 流式（互为 fallback）→ SSE 打字机 → 启发式 AI 率检测 → 结算/退款
- ✅ 降AI率模板（de_ai 工作流：检测前后对比）
- ✅ 焦耳账本：两阶段扣费、流水幂等、兑换码充值
- ✅ 管理后台：看板 / 模板 CRUD / 提示词版本 API / 兑换码批量 / 审核队列
- ✅ 事件流断线续传：`GET /works/{id}/stream?seq=N`

## 路线图（对照《05-项目开发计划》）

- [ ] M3：阿里云内容安全接入、自训检测模型（detector 微服务）
- [ ] M2-2.7：追问完整管道（当前仅记账）、换模板重写
- [ ] M4：灵感中心热点抓取、Milvus 做同款、看板图表
- [ ] 排版导出公众号富文本（MD→富文本转换器）

## 关键设计

- **提示词永不下发客户端**：`/template/detail` 只回 usage_example/tips（对标焦圈儿）
- **模型路由**：`app/core/config.py` 的 `MODEL_ROUTES`（default_chat/think/de_ai_rewrite/title_gen），DeepSeek 与 GLM 互为降级
- **幂等扣费**：所有焦耳变动写 `joule_transactions`，`idempotency_key` 唯一约束防重放
- **SSE 事件协议**：stage / search_end / delta / report / done / error，Redis List 存 30min 供续传
