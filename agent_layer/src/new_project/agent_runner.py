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

        # 优先使用旧的 pydantic 输出（如果未来重新启用 output_pydantic 仍可复用）
        milestones = getattr(milestones_output, "pydantic", None)
        funding_plan = getattr(funding_output, "pydantic", None)

        # DeepSeek 当前不支持 response_format，output_pydantic 已被注释，
        # 因此这里增加对原始文本输出的 JSON 解析兜底逻辑。
        if milestones is None or funding_plan is None:
            import json

            def _extract_json(raw_value, label: str):
                if raw_value is None:
                    return None
                text = str(raw_value)
                # 尝试截取第一个 {...} 作为 JSON 片段
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    text = text[start:end+1]
                try:
                    return json.loads(text)
                except Exception as e:
                    print(f"[AGENT][PARSE_ERROR] Failed to parse {label} as JSON: {e}. Raw=", text[:500])
                    return None

            raw_milestones = getattr(milestones_output, "raw", None) or getattr(milestones_output, "value", None) or getattr(milestones_output, "text", None)
            raw_funding = getattr(funding_output, "raw", None) or getattr(funding_output, "value", None) or getattr(funding_output, "text", None)

            milestones = _extract_json(raw_milestones, "milestones")
            funding_plan = _extract_json(raw_funding, "funding_plan")
        
        return {"status": "success", "milestones": milestones, "funding_plan": funding_plan}
    except Exception as e:
        return {"status": "error", "message": str(e)}
        
if __name__ == "__main__":
    run()

