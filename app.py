#!/usr/bin/env python
"""
MicroFund Agent Service
独立运行在 HF Spaces，只负责生成项目计划
主后端通过 HTTP 调用此服务，无需依赖 Render 的 DeepSeek 网络
"""
import sys
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Body

# 添加 agent_layer 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 只导入 Agent 相关的，不导入数据库等
from agent_layer.src.new_project.agent_runner import run

app = FastAPI(
    title="MicroFund Agent Service",
    description="独立的项目计划生成服务",
    version="1.0.0"
)


def _normalize_plan_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """宽松接收请求体并归一化为 agent_runner 所需字段，避免入口 422。"""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON body: expected object")

    # 兼容 snake_case / camelCase / 常见别名
    def pick(*keys: str):
        for k in keys:
            if k in payload and payload[k] is not None:
                return payload[k]
        return None

    normalized = {
        "project_name": pick("project_name", "projectName", "name"),
        "project_description": pick("project_description", "projectDescription", "description"),
        "project_domain": pick("project_domain", "projectDomain", "domain"),
        "project_duration": pick("project_duration", "projectDuration", "duration"),
        "team_size": pick("team_size", "teamSize"),
        "target_funding_amount": pick("target_funding_amount", "targetFundingAmount", "funding_goal", "fundingGoal"),
    }

    missing = [k for k, v in normalized.items() if v in (None, "")]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required fields",
                "missing_fields": missing,
                "received_keys": list(payload.keys()),
            },
        )

    # 类型归一化（字符串数字也接受）
    try:
        normalized["team_size"] = int(normalized["team_size"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid team_size: must be an integer")

    try:
        normalized["target_funding_amount"] = float(normalized["target_funding_amount"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid target_funding_amount: must be a number")

    # 其余字段强制转字符串，避免上游传入非字符串导致异常
    normalized["project_name"] = str(normalized["project_name"])
    normalized["project_description"] = str(normalized["project_description"])
    normalized["project_domain"] = str(normalized["project_domain"])
    normalized["project_duration"] = str(normalized["project_duration"])

    return normalized

@app.get("/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "microfund-agent-service",
        "version": "1.0.0"
    }

@app.post("/plan")
def generate_project_plan(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    生成项目计划的 API 端点
    
    Input:
    {
        "project_name": "GreenChain",
        "project_description": "A Web3 platform enabling carbon credit tokenization...",
        "project_domain": "Environmental DeFi",
        "project_duration": "3 months",
        "team_size": 3,
        "target_funding_amount": 10000
    }
    
    Output:
    {
        "status": "success",
        "milestones": {
            "milestones": [...]
        },
        "funding_plan": {
            "fundingstages": [...]
        }
    }
    """
    try:
        inputs = _normalize_plan_input(payload)
        print(f"[AGENT_SERVICE] Received plan request for project: {inputs.get('project_name')}")
        
        # 调用本地的 agent runner
        result = run(inputs)
        print(f"[AGENT_SERVICE] Generated plan: status={result.get('status')}")

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail="Agent returned non-dict result"
            )

        return result

    except Exception as e:
        print(f"[AGENT_SERVICE_ERROR] Plan generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Agent plan generation failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # HF Spaces 会自动设置 PORT 环境变量，默认 7860
    port = int(os.getenv("PORT", 7860))
    # 增加 timeout 到 120 秒，给 DeepSeek API 足够时间响应
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="info",
        timeout_keep_alive=120,  # 保持连接的超时
    )
