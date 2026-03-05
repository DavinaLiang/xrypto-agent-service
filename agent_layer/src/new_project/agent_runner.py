#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
import os

# 自动添加项目根目录到 sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # main.py 所在目录
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # new_project 的上一级目录
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    

from new_project.projectcreation_crew import NewProject
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def run(inputs: dict):
    """
    Run the CrewAI workflow with dynamic inputs.
    Args:
        inputs = {
            "project_name": "GreenChain",
            "project_description": "A Web3 platform enabling carbon credit tokenization and trading.",
            "project_domain": "Environmental DeFi",
            "project_duration": "3 months",
            "team_size": 3 ,
            "target_funding_amount": 10000
        }
    """
    try:
        crew_instance = NewProject().crew()
        crew_instance.kickoff(inputs=inputs)
        
        # 两个任务的结果都输出
        milestones_output = crew_instance.tasks[0].output
        funding_output = crew_instance.tasks[1].output

        # 直接获取 Pydantic 对象（因为已启用 output_pydantic）
        milestones = getattr(milestones_output, "pydantic", None)
        funding_plan = getattr(funding_output, "pydantic", None)

        print(f"[AGENT][MILESTONES_RESULT] {milestones}")
        print(f"[AGENT][FUNDING_PLAN_RESULT] {funding_plan}")
        
        if milestones is None:
            print(f"[AGENT][WARNING] Milestones Pydantic is None, raw output: {str(milestones_output)[:500]}")
        if funding_plan is None:
            print(f"[AGENT][WARNING] Funding Plan Pydantic is None, raw output: {str(funding_output)[:500]}")
        
        # 将 Pydantic 对象转换为字典（方便序列化）
        result = {
            "status": "success",
            "milestones": milestones.model_dump() if milestones else None,
            "funding_plan": funding_plan.model_dump() if funding_plan else None
        }
        
        print(f"[AGENT][RESULT] {result}")
        return result
    except Exception as e:
        import traceback
        print(f"[AGENT][ERROR] {str(e)}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
        
if __name__ == "__main__":
    run()

