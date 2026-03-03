#!/usr/bin/env python
"""
MicroFund Agent Service
独立运行在 HF Spaces，只负责生成项目计划
主后端通过 HTTP 调用此服务，无需依赖 Render 的 DeepSeek 网络
"""
import sys
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 添加 agent_layer 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 只导入 Agent 相关的，不导入数据库等
from agent_layer.src.new_project.agent_runner import run

class PlanInput(BaseModel):
    """项目计划生成的输入"""
    project_name: str
    project_description: str
    project_domain: str
    project_duration: str
    team_size: int
    target_funding_amount: float
    
    # 允许自动类型转换
    class Config:
        coerce_numbers_to_str = False

app = FastAPI(
    title="MicroFund Agent Service",
    description="独立的项目计划生成服务",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "microfund-agent-service",
        "version": "1.0.0"
    }

@app.post("/plan")
def generate_project_plan(payload: PlanInput) -> Dict[str, Any]:
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
        inputs = payload.model_dump()
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
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
