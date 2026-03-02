---
title: Xrytofund
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker  # 选项有: gradio, streamlit, docker, static
sdk_version: 5.0.0 # 建议写你本地用的版本，不确定就写这个最新的
app_file: app.py  
pinned: false
---
# Xrytofund Agent Service

独立的项目计划生成服务，运行在 HF Spaces，为主后端 (Render) 提供 AI 生成的项目计划。

## 文件结构

```
xrypto-agent-service/
├── app.py                    # FastAPI 应用入口
├── requirements.txt          # Python 依赖
├── Dockerfile               # HF Spaces 容器配置
├── .env.example            # 环境变量模板
├── README.md               # 本文件
└── agent_layer/            # 从 xrypto-backend 复制的 Agent 代码
    └── src/
        ├── new_project/           # 项目计划生成 Crew
        │   ├── projectcreation_crew.py
        │   ├── agent_runner.py
        │   └── ...
        └── proposal_agent/        # 评论/提案 Crew（可选）
            ├── proposalagent_runner.py
            └── ...
```

## 部署到 HF Spaces

### 前提条件
1. 有一个 GitHub 账号和仓库
2. 有一个 Hugging Face 账号

### 步骤

#### 1. 创建独立的 GitHub 仓库

```bash
git init xrypto-agent-service
cd xrypto-agent-service
git remote add origin https://github.com/your-username/xrypto-agent-service.git
```

把以下文件夹和文件推到这个仓库：
- `app.py`
- `requirements.txt`
- `Dockerfile`
- `.env.example`
- `agent_layer/` (从 xrypto-backend 复制)

#### 2. 在 HF Spaces 创建 Space

1. 打开 https://huggingface.co/spaces
2. 点击 "Create new Space"
3. 填写信息：
   - **Space name**: `xrypto-agent-service`
   - **License**: MIT
   - **Space SDK**: Docker
   - **Visibility**: Public
   - **Repository URL**: `https://github.com/your-username/xrypto-agent-service`

4. 点击 "Create Space"

#### 3. 设置环境变量

在 HF Space 的 **Settings** → **Variables and secrets** 中添加：

| Key | Value | 说明 |
|-----|-------|------|
| `DEEPSEEK_API_KEY` | `sk-xxx` | 你的 DeepSeek API Key |

#### 4. 验证部署

HF Spaces 会自动从 GitHub 拉取代码并构建。部署完成后：

```bash
curl https://your-username-xrypto-agent-service.hf.space/health
```

应该返回：
```json
{
  "status": "ok",
  "service": "microfund-agent-service",
  "version": "1.0.0"
}
```

## API 端点

### GET `/health`
健康检查

**响应**:
```json
{
  "status": "ok",
  "service": "microfund-agent-service",
  "version": "1.0.0"
}
```

### POST `/plan`
生成项目计划

**请求**:
```json
{
  "project_name": "GreenChain",
  "project_description": "A Web3 platform enabling carbon credit tokenization...",
  "project_domain": "Environmental DeFi",
  "project_duration": "3 months",
  "team_size": 3,
  "target_funding_amount": 10000
}
```

**响应**:
```json
{
  "status": "success",
  "milestones": {
    "milestones": [
      {
        "id": 1,
        "name": "Phase 1: Foundation",
        "description": "...",
        "expected_duration_months": 1,
        "deliverables": ["...", "..."],
        "success_criteria": ["...", "..."],
        "dependencies": null
      }
    ]
  },
  "funding_plan": {
    "fundingstages": [
      {
        "stage_name": "Seed",
        "tokens_allocated": 1000000,
        "unlock_condition": "...",
        "linked_milestone_id": 1,
        "rationale": "..."
      }
    ]
  }
}
```

## 集成到主后端

主后端 (Render) 在 `backend/services/agent_service.py` 中的 `generate_project_plan()` 函数：

```python
def generate_project_plan(inputs: dict) -> dict:
    external_url = os.getenv("PLAN_AGENT_URL")  # 设为 HF Space URL
    
    if external_url:
        resp = requests.post(external_url, json=inputs, timeout=60)
        return resp.json()
    
    # 回退到本地（开发环境）
    return run(inputs)
```

在 Render 后端的环境变量中设置：
```
PLAN_AGENT_URL=https://your-username-xrypto-agent-service.hf.space/plan
```

## 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DEEPSEEK_API_KEY="sk-xxx"

# 运行应用
python app.py

# 在另一个终端测试
curl -X POST http://localhost:7860/plan \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "Test",
    "project_description": "Test description",
    "project_domain": "DeFi",
    "project_duration": "3 months",
    "team_size": 3,
    "target_funding_amount": 10000
  }'
```

## 故障排除

### HF Space 显示 "Container failed to start"
- 检查 `DEEPSEEK_API_KEY` 环境变量是否正确设置
- 查看 HF Space 的日志（在 Space 主页的 "Logs" 选项卡）

### 调用 `/plan` 时返回 500
- 检查 `agent_layer/` 是否正确复制
- 验证 `projectcreation_crew.py` 和 `agent_runner.py` 的内容是否完整
- 查看 HF Space 的实时日志

### DeepSeek API 超时
- 这个仓库的目的就是为了解决 Render 到 DeepSeek 的网络问题
- 如果 HF Space 也超时，可能需要检查 DeepSeek API 的状态或 key 是否有效

## 许可证

MIT
