from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
import os
from dotenv import load_dotenv
from crewai import LLM

# Input models for comment aggregation
class CommentItem(BaseModel):
    id: int
    author_id: Optional[int] = None
    text: str
    created_at: Optional[str] = None
    endorsements: int = 0
    thread_context: Optional[str] = None

class CommentAggregation(BaseModel):
    project_id: int
    comments: List[CommentItem]
    analysis_window: Optional[str] = Field(
        default=None,
        description="Human-readable window, e.g. 'last_7_days' or 'latest_200'"
    )
    min_endorsements: int = Field(default=3, description="Minimum endorsements to consider")
    max_candidates: int = Field(default=5, description="Max ideas to promote per run")

# Output models for top ideas
ProposalIntent = Literal[
    "milestone_update",
    "fundingplan_update",
    "add_milestone",
    "add_fundingplan",
]

class TopIdea(BaseModel):
    proposal_intent: ProposalIntent
    confidence: float = Field(ge=0.0, le=1.0)
    source_comment_ids: List[int]
    idea_summary: str
    ranking_score: float = 0.0

class TopIdeas(BaseModel):
    project_id: int
    ideas: List[TopIdea]
    window_start: Optional[str] = None
    window_end: Optional[str] = None

# Single, concrete proposal output for monthly synthesis
class MonthlyProposalAuto(BaseModel):
    proposal_type: Literal["monthly_top_idea"] = "monthly_top_idea"
    title: str = Field(description="Concise title for the monthly top idea proposal")
    summary: str = Field(description="One paragraph summary of the proposal distilled from comments")
    details: str = Field(description="Concrete plan/details derived from monthly comments")
    source_comment_ids: List[int] = Field(default_factory=list, description="IDs of comments used to generate this proposal")
    explanation: Optional[str] = None

load_dotenv()

# Reuse DeepSeek config style to keep parity with existing crews
deepseek_llm = LLM(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0
)

@CrewBase
class CommentAnalysisCrew():
    """Crew to analyze comments and surface top community ideas."""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def comment_aggregator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['comment_aggregator_agent'],  # type: ignore[index]
            llm=deepseek_llm,
            verbose=True
        )

    @task
    def aggregate_top_ideas(self) -> Task:
        return Task(
            config=self.tasks_config['aggregate_top_ideas'],
            output_pydantic=TopIdeas
        )

    @task
    def synthesize_monthly_proposal(self) -> Task:
        """Summarize comments over a month and produce ONE concrete proposal."""
        return Task(
            config=self.tasks_config['synthesize_monthly_proposal'],
            output_pydantic=MonthlyProposalAuto
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
