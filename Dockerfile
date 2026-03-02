FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（可选，某些包可能需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个应用（包括 app.py 和 agent_layer）
COPY . .

# HF Spaces 使用 PORT 环境变量，默认 7860
EXPOSE 7860

# 启动应用
CMD ["python", "app.py"]
