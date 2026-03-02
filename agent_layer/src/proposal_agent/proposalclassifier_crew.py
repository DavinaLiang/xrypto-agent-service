from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai_tools import FileReadTool
from typing import List, Union
from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Any
import os
from litellm import completion
from dotenv import load_dotenv
from crewai import LLM

current_script_dir = os.path.dirname(os.path.abspath(__file__))
rules_file_path = os.path.join(current_script_dir, "rule.md")
file_read_tool = FileReadTool(file_path=rules_file_path)

# 定义【实际的】提案类型
PROPOSAL_TYPES = Literal[
    "milestone_update",
    "fundingplan_update",
    "add_milestone",
    "add_fundingplan",
    "regenerate_entire_plan",
]

# --- 1. Classification Model ---
class ProposalClassification(BaseModel):
    is_proposal: bool = Field(
        description="Set to True if the input text is a proposal requiring governance flow. Set to False if it is a general comment or idea."
    )
    # 使用 Optional 或 Union 来允许 None（即 JSON 中的 null）
    proposal_type: Optional[PROPOSAL_TYPES] = Field(
        description=(
            "If 'is_proposal' is True, select the most fitting type from the allowed proposal types. "
            "If 'is_proposal' is False, this field MUST be set to null (None)." # <--- 明确要求 null
        )
    )
    comment_content: str = Field(
description=(
        "If 'is_proposal' is False, this field MUST contain ONLY the original user input. "
        "It MUST NOT contain any instruction, rule, classification definition, or any text from the current task prompt. " # <--- 强调“绝不包含指令”
        "If 'is_proposal' is True, this field must be an empty string ('')."
        )
    )

# --- 2. Patch Model (for update_* types) ---
class ProposalDraft(BaseModel):
    # A compact, machine-actionable patch suggestion that maps to a DB field.
    table: Literal["milestones", "funding_plan"] = Field(
        description="Target table for the patch: 'milestones' or 'funding_plan'"
    )
    id: int = Field(description="The existing record id to update")
    field: str = Field(description="The column/field to update on the record")
    new_value: Any = Field(description="The new value to set for the field (string/number)")
    summary: str = Field(description="One short human-friendly sentence describing the change")


# --- 3. Addition Models (for add_* types) ---
class MilestoneAddition(BaseModel):
    """Schema for suggesting a new milestone to be added to the project."""
    name: str = Field(
        description="A concise name for the new milestone",
        min_length=1,
        max_length=100
    )
    description: str = Field(
        description="Detailed description of what this milestone entails",
        min_length=1,
        max_length=1000
    )
    expected_duration_months: int = Field(
        description="Expected duration to complete this milestone in months",
        ge=1,
        le=60
    )
    deliverables: str = Field(
        description="Key deliverables for this milestone",
        default=""
    )
    success_criteria: str = Field(
        description="Criteria to measure successful completion",
        default=""
    )
    dependencies: str = Field(
        description="Any dependencies on other milestones",
        default=""
    )
    summary: str = Field(
        description="One-line human-friendly summary for UI display",
        min_length=1,
        max_length=200
    )
    rationale: str = Field(
        description="Why this milestone is needed based on the user's input",
        min_length=1,
        max_length=500
    )


class FundingPlanAddition(BaseModel):
    """Schema for suggesting a new funding stage to be added to the project."""
    stage_name: str = Field(
        description="Name of the new funding stage",
        min_length=1,
        max_length=100
    )
    tokens_allocated: int = Field(
        description="Number of tokens to allocate for this stage",
        ge=1
    )
    unlock_condition: str = Field(
        description="Condition under which these tokens are unlocked",
        min_length=1,
        max_length=500
    )
    linked_milestone_id: Optional[int] = Field(
        description="Optional: id of the milestone this stage is linked to",
        default=None
    )
    summary: str = Field(
        description="One-line human-friendly summary for UI display",
        min_length=1,
        max_length=200
    )
    rationale: str = Field(
        description="Why this funding stage is needed based on the user's input",
        min_length=1,
        max_length=500
    )


# --- 4. Proposal output types ---
class ProposalDrafts(BaseModel):
    """Output when proposal_type is milestone_update or fundingplan_update: contains patch suggestions."""
    proposal_type: Literal["milestone_update", "fundingplan_update"] = Field(
        description="Proposal type: must be update_* variant"
    )
    drafts: List[ProposalDraft] = Field(
        description="List of patch suggestions to modify existing records",
        min_items=0,
        max_items=5,
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Optional explanation if no drafts or additional context"
    )


class ProposalAdditions(BaseModel):
    """Output when proposal_type is add_milestone or add_fundingplan: contains new record suggestions."""
    proposal_type: Literal["add_milestone", "add_fundingplan"] = Field(
        description="Proposal type: must be add_* variant"
    )
    additions: Union[List[MilestoneAddition], List[FundingPlanAddition]] = Field(
        description="List of new records to add. If proposal_type is add_milestone, items are MilestoneAddition. If add_fundingplan, items are FundingPlanAddition.",
        min_items=1,
        max_items=3,
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Optional explanation for the suggestions"
    )
    
load_dotenv()

# 初始化 Deepseek v3 模型
deepseek_llm = LLM(
    model="deepseek-chat",                  
    base_url="https://api.deepseek.com/v1",  # DeepSeek 的 OpenAI 兼容接口
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

@CrewBase
class GovernanceCrew():
    """NewProject crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    @agent
    def proposal_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['proposal_agent'], # type: ignore[index]
            llm=deepseek_llm,
            tools = [file_read_tool],
            verbose=True
        )
    
    @agent
    def proposal_writer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['proposal_writer_agent'], # type: ignore[index]
            llm=deepseek_llm,
            verbose=True
        )
    
    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def classify_input(self) -> Task:
        return Task(
            config=self.tasks_config['classify_input'],
            output_pydantic=ProposalClassification
        )
    
    @task
    def generate_update_drafts(self) -> Task:
        return Task(
            config=self.tasks_config['generate_update_drafts'],
            output_pydantic=ProposalDrafts
        )

    @task
    def generate_addition_drafts(self) -> Task:
        return Task(
            config=self.tasks_config['generate_addition_drafts'],
            output_pydantic=ProposalAdditions
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
