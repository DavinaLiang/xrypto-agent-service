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

