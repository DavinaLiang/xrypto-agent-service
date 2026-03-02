#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
import os
import json

# 自动添加项目根目录到 sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # main.py 所在目录
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))  # new_project 的上一级目录
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    

from proposal_agent.proposalclassifier_crew import GovernanceCrew, ProposalClassification, ProposalDrafts, ProposalAdditions
from proposal_agent.commentanalysis_crew import (
    CommentAnalysisCrew,
    CommentAggregation,
    TopIdeas,
    MonthlyProposalAuto,
)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def _extract_json_like(obj):
    """Try several fallback strategies to extract a JSON string or dict from the Crew result."""
    if obj is None:
        return None
    if isinstance(obj, (str, bytes, bytearray)):
        return obj if isinstance(obj, str) else obj.decode()
    if isinstance(obj, dict):
        return obj

    # Pydantic models
    if hasattr(obj, "model_dump_json"):
        try:
            return obj.model_dump_json()
        except Exception:
            pass
    if hasattr(obj, "model_dump"):
        try:
            return json.dumps(obj.model_dump(), ensure_ascii=False)
        except Exception:
            pass

    # Common wrapper attributes
    for attr in ("final_output", "final", "output", "raw", "result", "pydantic", "json_dict"):
        if hasattr(obj, attr):
            val = getattr(obj, attr)
            if val is None:
                continue
            if isinstance(val, (str, dict)):
                return val
            if hasattr(val, "model_dump"):
                try:
                    return json.dumps(val.model_dump(), ensure_ascii=False)
                except Exception:
                    pass
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                try:
                    return str(val)
                except Exception:
                    continue

    try:
        return str(obj)
    except Exception:
        return None


def _normalize_extracted(extracted):
    """Normalize the extracted value into a plain dict.

    Many Crew outputs are wrapped objects that serialize to JSON like:
    {"raw": "{...}", "tasks_output": [...]} where the true JSON lives
    inside the `raw` field (or inside a task's `raw`). This helper will
    attempt to unwrap those layers and return the innermost dict when
    possible.
    """
    if extracted is None:
        return None

    # If it's already a dict, use it (but still try to unwrap embedded 'raw')
    parsed = None
    if isinstance(extracted, dict):
        parsed = extracted
    elif isinstance(extracted, str):
        try:
            parsed = json.loads(extracted)
        except Exception:
            # Not JSON, nothing to normalize
            return extracted
    else:
        # Fallback: try to convert to string then parse
        try:
            parsed = json.loads(str(extracted))
        except Exception:
            return str(extracted)

    # If parsed is not a dict, return as-is
    if not isinstance(parsed, dict):
        return parsed

    # If there's a top-level 'raw' that contains a JSON string, parse it
    for key in ("raw", "final_output", "output", "result"):
        if key in parsed and isinstance(parsed[key], str):
            try:
                inner = json.loads(parsed[key])
                if isinstance(inner, dict):
                    return inner
                # if it's a JSON string nested further, keep drilling
                parsed = inner
            except Exception:
                # not JSON inside, ignore
                pass

    # If tasks_output contains task-level raw JSON, prefer that
    tasks = parsed.get("tasks_output")
    if isinstance(tasks, list) and tasks:
        for t in tasks:
            if isinstance(t, dict) and isinstance(t.get("raw"), str):
                try:
                    inner = json.loads(t.get("raw"))
                    if isinstance(inner, dict):
                        return inner
                except Exception:
                    pass

    # Nothing more to unwrap, return the parsed dict
    return parsed


def run_proposal_flow(user_input: str, project_context: dict | None = None, run_drafting: bool = True):
    """Run a two-step classification -> drafting flow using CrewAI crews.

    This function is intentionally small and explicit: it creates a crew instance,
    runs only the classification task with a dict of inputs, parses the output
    into the Pydantic model, and if needed runs the drafting task.
    """
    try:
        print(f"[RUNNER DEBUG] run_proposal_flow called with user_input (type={type(user_input)}): {repr(user_input)[:1000]}, run_drafting={run_drafting}")

        # Initialize the crew instance (class decorated with @CrewBase)
        crew_instance = GovernanceCrew()

        # Build and run only the classification task
        classification_task = crew_instance.classify_input()
        classification_crew = crew_instance.crew()
        classification_crew.tasks = [classification_task]

        inputs = {"user_input": user_input}
        raw_classification = classification_crew.kickoff(inputs=inputs)
        print("[DEBUG] classification kickoff returned type:", type(raw_classification))

        extracted = _extract_json_like(raw_classification)
        print("[DEBUG] classification extracted:", extracted)

        result_dict = _normalize_extracted(extracted)
        # If normalization returned a JSON string, parse it
        if isinstance(result_dict, str):
            try:
                result_dict = json.loads(result_dict)
            except Exception:
                result_dict = {"raw": result_dict}

        if not isinstance(result_dict, dict):
            raise ValueError(f"Unable to normalize classification result into dict: {type(result_dict)}")

        classification = ProposalClassification(**result_dict)

        # If caller only wanted classification, return it as dict
        if not run_drafting:
            return classification.model_dump()

        if not classification.is_proposal:
            return {"status": "comment_saved", "content": classification.comment_content}

        # It's a proposal -> run drafting
        # Select the correct task based on proposal_type
        if classification.proposal_type in ("milestone_update", "fundingplan_update"):
            drafting_task = crew_instance.generate_update_drafts()
        elif classification.proposal_type in ("add_milestone", "add_fundingplan"):
            drafting_task = crew_instance.generate_addition_drafts()
        else:
            # Fallback or error if type is unknown
            raise ValueError(f"Unknown proposal_type for drafting: {classification.proposal_type}")

        drafting_crew = crew_instance.crew()
        drafting_crew.tasks = [drafting_task]

        drafting_inputs = {"user_input": user_input, "proposal_type": classification.proposal_type}
        # include project_context (serialized DB snapshot) when provided so drafting agent can reference real data
        if project_context is not None:
            drafting_inputs["project_context"] = project_context
        raw_drafting = drafting_crew.kickoff(inputs=drafting_inputs)
        print("[DEBUG] drafting kickoff returned type:", type(raw_drafting))

        extracted_drafting = _extract_json_like(raw_drafting)
        print("[DEBUG] drafting extracted:", extracted_drafting)

        draft_dict = _normalize_extracted(extracted_drafting)
        if isinstance(draft_dict, str):
            try:
                draft_dict = json.loads(draft_dict)
            except Exception:
                draft_dict = {"raw": draft_dict}

        if not isinstance(draft_dict, dict):
            raise ValueError(f"Unable to normalize drafting result into dict: {type(draft_dict)}")

        # Determine which output model to use based on proposal_type
        proposal_type = draft_dict.get("proposal_type")
        
        if proposal_type in ("milestone_update", "fundingplan_update"):
            # Output is ProposalDrafts (patches)
            drafts_output = ProposalDrafts(**draft_dict)
            return {
                "status": "drafts_generated",
                "proposal_type": drafts_output.proposal_type,
                "drafts": [d.model_dump() for d in drafts_output.drafts],
                "explanation": drafts_output.explanation
            }
        elif proposal_type in ("add_milestone", "add_fundingplan"):
            # Output is ProposalAdditions (new records)
            additions_output = ProposalAdditions(**draft_dict)
            return {
                "status": "additions_generated",
                "proposal_type": additions_output.proposal_type,
                "additions": [a.model_dump() for a in additions_output.additions],
                "explanation": additions_output.explanation
            }
        else:
            raise ValueError(f"Unknown proposal_type in drafting output: {proposal_type}")

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print("[AGENT ERROR] Exception while running proposal flow:\n", tb)
        return {"error": f"Agent execution failed: {str(e)}", "trace": tb}

def run_comment_to_proposal_flow(
    project_id: int,
    comments: list,
    project_context: dict | None = None,
    thresholds: dict | None = None,
):
    """Analyze comments and convert top ideas into proposal drafts/additions.

    Returns a dict with candidates and their generated outputs ready for proposal creation.
    """
    try:
        # Prepare aggregation input
        agg = CommentAggregation(
            project_id=project_id,
            comments=[
                {
                    "id": c.get("id"),
                    "author_id": c.get("author_id"),
                    "text": c.get("text") or c.get("content") or "",
                    "created_at": c.get("created_at"),
                    "endorsements": c.get("endorsements", 0),
                    "thread_context": c.get("thread_context"),
                }
                for c in comments
            ],
            min_endorsements=(thresholds or {}).get("min_endorsements", 3),
            max_candidates=(thresholds or {}).get("max_candidates", 5),
            analysis_window=(thresholds or {}).get("analysis_window"),
        )

        # Run comment analysis crew
        analysis_instance = CommentAnalysisCrew()
        task = analysis_instance.aggregate_top_ideas()
        crew = analysis_instance.crew()
        crew.tasks = [task]
        top_ideas_raw = crew.kickoff(inputs={"aggregation": agg.model_dump()})

        extracted = _extract_json_like(top_ideas_raw)
        normalized = _normalize_extracted(extracted)
        if isinstance(normalized, str):
            try:
                normalized = json.loads(normalized)
            except Exception:
                normalized = {"raw": normalized}
        
        top_ideas = TopIdeas(**normalized)

        # For each idea, route to existing drafting tasks
        governance = GovernanceCrew()
        outputs = []
        for idea in top_ideas.ideas:
            # Classify the idea_summary to determine the concrete proposal_type
            cls_instance = GovernanceCrew()
            cls_task = cls_instance.classify_input()
            cls_crew = cls_instance.crew()
            cls_crew.tasks = [cls_task]
            cls_raw = cls_crew.kickoff(inputs={"user_input": idea.idea_summary})
            cls_ex = _extract_json_like(cls_raw)
            cls_norm = _normalize_extracted(cls_ex)
            if isinstance(cls_norm, str):
                try:
                    cls_norm = json.loads(cls_norm)
                except Exception:
                    cls_norm = {"raw": cls_norm}
            
            cls_model = ProposalClassification(**cls_norm)
            if not cls_model.is_proposal or not cls_model.proposal_type:
                # Skip ideas that aren't proposals after classification
                continue
            proposal_type = cls_model.proposal_type
            if proposal_type in ("milestone_update", "fundingplan_update"):
                drafting_task = governance.generate_update_drafts()
            elif proposal_type in ("add_milestone", "add_fundingplan"):
                drafting_task = governance.generate_addition_drafts()
            else:
                continue

            drafting_crew = governance.crew()
            drafting_crew.tasks = [drafting_task]

            drafting_inputs = {
                "user_input": idea.idea_summary,
                "proposal_type": proposal_type,
            }
            if project_context is not None:
                drafting_inputs["project_context"] = project_context

            raw = drafting_crew.kickoff(inputs=drafting_inputs)
            dr_ex = _extract_json_like(raw)
            dr_norm = _normalize_extracted(dr_ex)
            if isinstance(dr_norm, str):
                try:
                    dr_norm = json.loads(dr_norm)
                except Exception:
                    dr_norm = {"raw": dr_norm}

            # Wrap with metadata for API creation later
            outputs.append({
                "project_id": project_id,
                "proposal_type": proposal_type,
                "source_comment_ids": idea.source_comment_ids,
                "confidence": idea.confidence,
                "idea_summary": idea.idea_summary,
                "drafting_output": dr_norm,
            })

        return {
            "status": "ideas_processed",
            "project_id": project_id,
            "candidates": outputs,
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("[AGENT ERROR] Exception while running comment->proposal flow:\n", tb)
        return {"error": f"Comment analysis failed: {str(e)}", "trace": tb}

def run_monthly_comment_summary_proposal(
    project_id: int,
    comments: list,
    project_context: dict | None = None,
    thresholds: dict | None = None,
):
    """Summarize last-month comments and produce ONE concrete proposal (no classification).

    The output is directly compatible with your proposal creation API
    (contains either drafts for updates or additions for new records).
    """
    try:
        agg = CommentAggregation(
            project_id=project_id,
            comments=[
                {
                    "id": c.get("id"),
                    "author_id": c.get("author_id"),
                    "text": c.get("text") or c.get("content") or "",
                    "created_at": c.get("created_at"),
                    "endorsements": c.get("endorsements", 0),
                    "thread_context": c.get("thread_context"),
                }
                for c in comments
            ],
            min_endorsements=(thresholds or {}).get("min_endorsements", 3),
            max_candidates=(thresholds or {}).get("max_candidates", 5),
            analysis_window=(thresholds or {}).get("analysis_window", "last_30_days"),
        )

        analysis_instance = CommentAnalysisCrew()
        task = analysis_instance.synthesize_monthly_proposal()
        crew = analysis_instance.crew()
        crew.tasks = [task]

        inputs = {"aggregation": agg.model_dump()}
        if project_context is not None:
            inputs["project_context"] = project_context

        raw = crew.kickoff(inputs=inputs)
        ex = _extract_json_like(raw)
        norm = _normalize_extracted(ex)
        if isinstance(norm, str):
            try:
                norm = json.loads(norm)
            except Exception:
                norm = {"raw": norm}

        monthly = MonthlyProposalAuto(**norm)
        payload: dict = {
            "proposal_type": monthly.proposal_type,
            "title": monthly.title,
            "summary": monthly.summary,
            "details": monthly.details,
            "source_comment_ids": monthly.source_comment_ids,
        }

        return {
            "status": "monthly_proposal_ready",
            "project_id": project_id,
            "proposal_type": monthly.proposal_type,
            "payload": payload,
            "explanation": monthly.explanation,
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("[AGENT ERROR] Exception while running monthly summary flow:\n", tb)
        return {"error": f"Monthly summary failed: {str(e)}", "trace": tb}

# --- Example Usage ---
if __name__ == "__main__":
    # Example: A Formal Proposal
    proposal_input = "We need to update Milestone 3 because the required security audit tool has been deprecated. We should replace the 'Static Code Checker X' task with 'Automated Scanner Y' which covers the same scope but is actively maintained. This should take 3 extra days."
    print(f"--- Running Flow with Input: '{proposal_input}' ---")
    result_proposal = run_proposal_flow(proposal_input)
    print("\n\n--- FINAL OUTPUT (PROPOSAL DRAFTS) ---")
    print(json.dumps(result_proposal, indent=2, ensure_ascii=False))
