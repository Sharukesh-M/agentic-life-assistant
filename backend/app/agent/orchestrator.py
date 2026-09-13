"""
JARVIX Master Orchestrator Agent.
Connects User Request -> Context -> Database Memory/State -> LLM -> Validation -> Safety Decision Engine -> Capability Execution -> Persistence -> Response.
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, List

from app.agent.prompt_loader import assemble_agent_prompt
from app.agent.agent_context import AgentContext
from app.agent.decision_engine import DecisionEngine
from app.agent.routing import RoutingDispatcher
from app.llm.base import BaseLLMProvider
from app.llm.provider import get_llm_provider
from app.schemas.orchestration import OrchestratorRouting
from app.schemas.planning import PlanOutput, ClarificationOutput

from app.tools.executor import ToolExecutor
from app.tools.context import ToolExecutionContext
from app.schemas.tool_use import ToolCallRequest

logger = logging.getLogger("jarvix.orchestrator")

class JARVIXOrchestrator:
    """
    JARVIX End-to-End Agent Orchestrator with Database & Tiered Memory Integration.
    """

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None, tool_executor: Optional[ToolExecutor] = None):
        self.llm_provider = llm_provider or get_llm_provider()
        self.decision_engine = DecisionEngine()
        self.routing_dispatcher = RoutingDispatcher()
        self.tool_executor = tool_executor or ToolExecutor()

    def route_request(self, user_request: str, context: AgentContext) -> OrchestratorRouting:
        """
        Calls LLM with Orchestrator Prompt to obtain validated routing decision.
        """
        system_prompt = assemble_agent_prompt("orchestration/orchestrator.md")
        user_prompt = f"""
USER_CONTEXT:
- Active Goals Count: {len(context.active_goals)}
- Existing Tasks Count: {len(context.existing_tasks)}
- Retrieved Memories: {context.retrieved_memories}

CURRENT_USER_REQUEST:
"{user_request}"
"""

        llm_resp = self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format_json=True
        )

        if not llm_resp.success:
            logger.error(f"[Orchestrator Error] LLM call failed: {llm_resp.error_message}")
            return OrchestratorRouting(
                intent="general_conversation",
                required_capabilities=["General Conversation"],
                required_tools=[],
                authorization_checked=True,
                authorization_status="not_applicable",
                requires_confirmation=False
            )

        # Parse & Validate JSON output
        parsed_dict = llm_resp.parsed_json
        if not parsed_dict and llm_resp.text:
            try:
                parsed_dict = json.loads(llm_resp.text)
            except Exception:
                parsed_dict = None

        if not parsed_dict:
            logger.warning("[Orchestrator Warning] Malformed routing JSON from LLM. Falling back to default routing.")
            routing = OrchestratorRouting(
                intent="general_conversation",
                required_capabilities=["General Conversation"],
                required_tools=[],
                authorization_checked=True,
                authorization_status="not_applicable",
                requires_confirmation=False
            )
        else:
            try:
                routing = OrchestratorRouting(**parsed_dict)
            except Exception as e:
                logger.warning(f"[Orchestrator Schema Warning] Schema validation failed ({e}). Falling back.")
                routing = OrchestratorRouting(
                    intent="general_conversation",
                    required_capabilities=["General Conversation"],
                    required_tools=[],
                    authorization_checked=True,
                    authorization_status="not_applicable",
                    requires_confirmation=False
                )

        # Application-Level Safety Enforcement (DecisionEngine overrides LLM)
        for tool in routing.required_tools:
            if not self.decision_engine.is_action_reversible(tool, {}):
                routing.requires_confirmation = True
                if not routing.confirmation_prompt:
                    routing.confirmation_prompt = f"Action '{tool}' is high-impact and requires your explicit confirmation before execution."

        return routing

    def execute_planning(self, user_request: str, context: AgentContext, db_session: Optional[Any] = None) -> Dict[str, Any]:
        """
        Executes Planning Capability via Planning Agent Prompt + LLM + Pydantic Schema Validation.
        Optionally persists validated Plan into Goal, Milestone, and Task DB models.
        """
        system_prompt = assemble_agent_prompt("planning/planning_agent.md")
        user_prompt = f"""
GOAL: {user_request}
USER_PROFILE: {json.dumps(context.user_profile)}
PREFERENCES: {json.dumps(context.preferences)}
AVAILABILITY: 2 hours per day
EXISTING_TASKS: {json.dumps(context.existing_tasks)}
DEADLINE: None specified
"""

        llm_resp = self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format_json=True
        )

        if not llm_resp.success:
            return {
                "success": False,
                "error": llm_resp.error_message or "Planning execution failed."
            }

        parsed_dict = llm_resp.parsed_json
        if not parsed_dict and llm_resp.text:
            try:
                parsed_dict = json.loads(llm_resp.text)
            except Exception:
                parsed_dict = None

        if not parsed_dict:
            return {
                "success": False,
                "error": "Failed to parse planning response into valid JSON."
            }

        status = parsed_dict.get("status")
        if status == "plan":
            try:
                plan_obj = PlanOutput(**parsed_dict)
                
                # Persist Goal, Milestones, and Tasks into Database if session is active
                if db_session:
                    self._persist_plan_to_db(plan_obj, context.user_id, db_session)

                return {
                    "success": True,
                    "type": "plan",
                    "data": plan_obj if isinstance(plan_obj, dict) else plan_obj.__dict__
                }
            except Exception as e:
                return {"success": False, "error": f"Plan schema validation failed: {str(e)}"}
        elif status == "clarification_needed":
            try:
                clar_obj = ClarificationOutput(**parsed_dict)
                return {
                    "success": True,
                    "type": "clarification_needed",
                    "data": clar_obj if isinstance(clar_obj, dict) else clar_obj.__dict__
                }
            except Exception as e:
                return {"success": False, "error": f"Clarification schema validation failed: {str(e)}"}
        else:
            return {"success": False, "error": f"Unknown planning status '{status}' returned."}

    def _persist_plan_to_db(self, plan: PlanOutput, user_id: str, db_session: Any):
        """
        Helper method to write validated PlanOutput object into PostgreSQL/DB tables.
        """
        try:
            from app.db.repositories.user_repository import UserRepository
            from app.db.repositories.goal_repository import GoalRepository
            from app.db.repositories.task_repository import TaskRepository

            user_repo = UserRepository(db_session)
            user_repo.get_or_create(user_id)

            goal_repo = GoalRepository(db_session)
            task_repo = TaskRepository(db_session)

            goal_id = f"goal_{uuid.uuid4().hex[:12]}"
            goal_title = plan.goal if hasattr(plan, "goal") else plan.get("goal", "New Goal")
            
            # Create Goal record
            goal_repo.create_goal(
                goal_id=goal_id,
                user_id=user_id,
                title=goal_title,
                category="General",
                description=f"Assumptions: {plan.assumptions if hasattr(plan, 'assumptions') else plan.get('assumptions', [])}"
            )

            milestones = plan.milestones if hasattr(plan, "milestones") else plan.get("milestones", [])
            for idx, ms in enumerate(milestones):
                ms_id = f"ms_{uuid.uuid4().hex[:12]}"
                ms_title = ms.title if hasattr(ms, "title") else ms.get("title")
                ms_desc = ms.description if hasattr(ms, "description") else ms.get("description")

                goal_repo.add_milestone(
                    milestone_id=ms_id,
                    goal_id=goal_id,
                    title=ms_title,
                    description=ms_desc,
                    order_index=idx
                )

                tasks = ms.tasks if hasattr(ms, "tasks") else ms.get("tasks", [])
                for t in tasks:
                    t_id = f"task_{uuid.uuid4().hex[:12]}"
                    t_title = t.title if hasattr(t, "title") else t.get("title")
                    t_desc = t.description if hasattr(t, "description") else t.get("description")
                    t_prio = t.priority if hasattr(t, "priority") else t.get("priority", "MEDIUM")
                    t_mins = t.estimated_minutes if hasattr(t, "estimated_minutes") else t.get("estimated_minutes", 30)

                    task_repo.create_task(
                        task_id=t_id,
                        goal_id=goal_id,
                        milestone_id=ms_id,
                        user_id=user_id,
                        title=t_title,
                        description=t_desc,
                        priority=t_prio,
                        estimated_minutes=t_mins
                    )
        except Exception as e:
            logger.error(f"[Orchestrator DB Persist Error] Failed to persist plan: {str(e)}")

    def execute_general_conversation(self, user_request: str, context: AgentContext) -> Dict[str, Any]:
        """
        Executes General Conversation Fallback Capability.
        """
        system_prompt = assemble_agent_prompt(
            specialist_prompt_path="response/response_policy.md",
            include_hallucination_overlay=True,
            include_safety_overlay=True,
            include_error_overlay=True
        )

        memories_ctx = f"RELEVANT_USER_MEMORIES: {context.retrieved_memories}\n" if context.retrieved_memories else ""
        user_prompt = f"{memories_ctx}USER_MESSAGE: \"{user_request}\""

        llm_resp = self.llm_provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format_json=False
        )

        if not llm_resp.success:
            return {
                "success": False,
                "error": llm_resp.error_message or "General conversation failed."
            }

        return {
            "success": True,
            "response": llm_resp.text
        }

    def execute_pipeline(
        self,
        user_request: str,
        context: Optional[AgentContext] = None,
        db_session: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Main End-to-End Stateful Pipeline:
        User Request -> DB Memory/State Load -> Context -> Orchestrator -> LLM Routing -> Decision Engine -> Capability Execution -> DB Persistence -> Validated Response
        """
        start_time = time.time()
        user_id = context.user_id if context else "default_user"

        # Load bounded persistent context from DB if session provided
        if db_session:
            context = AgentContext.load_from_db(user_id=user_id, query=user_request, session=db_session)
        elif context is None:
            context = AgentContext(user_id=user_id)

        # Step 1: Orchestrator LLM Route Request
        routing = self.route_request(user_request, context)

        # Step 2: Confirmation Gate (Safety Engine)
        if routing.requires_confirmation:
            res = {
                "status": "requires_confirmation",
                "intent": routing.intent,
                "required_capabilities": routing.required_capabilities,
                "confirmation_prompt": routing.confirmation_prompt,
                "latency_seconds": time.time() - start_time
            }
            self._log_agent_run(user_id, routing, res, db_session, start_time)
            return res

        # Step 3: Tool Execution (if tools are required by routing)
        tool_results = []
        if routing.required_tools:
            tool_ctx = ToolExecutionContext(
                user_id=user_id,
                db_session=db_session,
                confirmed_by_user=not routing.requires_confirmation
            )
            for tool_name in routing.required_tools:
                req = ToolCallRequest(
                    tool_name=tool_name,
                    arguments={},
                    necessity_rationale=f"Required for intent '{routing.intent}'"
                )
                t_res = self.tool_executor.execute_tool(req, tool_ctx)
                tool_results.append(t_res)

        # Step 4: Capability Execution & DB State Update
        capability_result = None
        if "Planning" in routing.required_capabilities or "Goal Management" in routing.required_capabilities:
            capability_result = self.execute_planning(user_request, context, db_session=db_session)
        else:
            capability_result = self.execute_general_conversation(user_request, context)

        if tool_results:
            capability_result["tool_results"] = [
                res.__dict__ if hasattr(res, "__dict__") else res for res in tool_results
            ]

        total_latency = time.time() - start_time
        final_status = "completed" if capability_result.get("success") else "error"

        pipeline_res = {
            "status": final_status,
            "intent": routing.intent,
            "required_capabilities": routing.required_capabilities,
            "required_tools": routing.required_tools,
            "authorization_status": routing.authorization_status,
            "result": capability_result,
            "provider": getattr(self.llm_provider, "config", None).provider if hasattr(self.llm_provider, "config") else "mock",
            "latency_seconds": total_latency
        }

        # Step 4: Observability Log in AgentRunRepository
        self._log_agent_run(user_id, routing, pipeline_res, db_session, start_time)

        return pipeline_res

    def _log_agent_run(self, user_id: str, routing: OrchestratorRouting, result: dict, db_session: Optional[Any], start_time: float):
        """Logs execution run record in database for observability."""
        if not db_session:
            return
        try:
            from app.db.repositories.agent_run_repository import AgentRunRepository
            run_repo = AgentRunRepository(db_session)
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            latency_ms = (time.time() - start_time) * 1000.0

            run_repo.create_run_record(
                run_id=run_id,
                user_id=user_id,
                intent=routing.intent,
                required_capabilities=routing.required_capabilities,
                required_tools=routing.required_tools,
                provider=result.get("provider", "mock"),
                model="jarvix-engine",
                confirmation_required=routing.requires_confirmation,
                execution_status=result.get("status", "completed"),
                validation_status="valid" if result.get("status") == "completed" else "error",
                latency_ms=latency_ms
            )
        except Exception as e:
            logger.error(f"[Orchestrator Observability Error] Failed to log agent run: {str(e)}")
