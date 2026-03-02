from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from litellm import completion
from dotenv import load_dotenv
from crewai import LLM

class Milestone(BaseModel):
    id: int = Field(..., description="Sequential ID of the milestone")
    name: str = Field(..., description="Milestone title or key achievement name")
    description: str = Field(..., description="Detailed explanation of milestone goal and scope")
    expected_duration_months: int = Field(..., description="Estimated duration in months to complete this milestone")
    deliverables: List[str] = Field(..., description="List of tangible outputs or results expected")
    success_criteria: List[str] = Field(..., description="Conditions or metrics used to validate milestone completion")
    dependencies: Optional[List[int]] = Field(default=None, description="IDs of dependent milestones if any")

class MilestonePlan(BaseModel):
    milestones: List[Milestone]
    
class FundingStage(BaseModel):
    stage_name: str = Field(..., description="Name of the funding stage, e.g., Seed, Private, Public")
    tokens_allocated: float = Field(..., description="Number of tokens allocated to this stage")
    unlock_condition: str = Field(..., description="Condition or milestone required to unlock this stage’s tokens")
    linked_milestone_id: int = Field(..., description="ID of the related milestone from the project plan")
    rationale: str = Field(..., description="Reasoning for allocation and release design of this stage")

class FundingPlan(BaseModel):
    fundingstages: List[FundingStage]
    
load_dotenv()
# 初始化 Deepseek v3 模型
deepseek_llm = LLM(
    model="deepseek-chat",                  
    base_url="https://api.deepseek.com/v1",  # DeepSeek 的 OpenAI 兼容接口
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

@CrewBase
class NewProject():
    """NewProject crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def project_planner(self) -> Agent:
        return Agent(
            config=self.agents_config['project_planner'], # type: ignore[index]
            llm=deepseek_llm,
            verbose=True
        )

    @agent
    def funding_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config['funding_strategist'], # type: ignore[index]
            llm=deepseek_llm,
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def generate_milestones(self) -> Task:
        return Task(
            config=self.tasks_config['generate_milestones'],
            # NOTE: 之前这里使用 output_pydantic=MilestonePlan，会触发 CrewAI 使用
            # response_format 进行结构化输出，DeepSeek 当前版本已不再支持该类型，
            # 因此暂时注释掉，改为在服务层手动解析 JSON 文本。
            # output_pydantic=MilestonePlan
        )

    @task
    def generate_funding_plan(self) -> Task:
        return Task(
            config=self.tasks_config['generate_funding_plan'],
            #context=[self.generate_milestones],
            # 同上，暂时不用 Pydantic 自动结构化，避免 DeepSeek 400 错误。
            # output_pydantic=FundingPlan
        )

    @crew
    def crew(self) -> Crew:
        """Creates the NewProject crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
