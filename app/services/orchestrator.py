import json
from typing import Optional
from sqlalchemy.orm import Session
from app.services.session_store import session_store
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.tool_router import tool_router
from app.services.metrics import metrics
from app.guardrails import check_input_safety, check_response_safety
from app.logger import logger


class Orchestrator:
    """
    Central conversation controller.
    Ties together: session → RAG → LLM → tools → response.
    """

    async def process_message(
        self,
        user_message: str,
        session_id: Optional[str],
        db: Session,
    ) -> dict:
        """
        Process a user message through the full pipeline.

        Returns:
            {
                "reply": str,
                "session_id": str,
                "user_type": str,
                "verified": bool,
            }
        """
        # 1. Get or create session
        session = session_store.get_or_create_session(session_id)
        sid = session["session_id"]

        # 2. Check input safety
        is_safe, warning = check_input_safety(user_message)

        # 3. Add user message to history
        session_store.add_message(sid, "user", user_message)

        # 4. Retrieve RAG context (guests only see public docs)
        access_level = "all" if session.get("verified") else "public"
        with metrics.timer("rag_latency_ms"):
            rag_context = rag_service.retrieve(user_message, top_k=4, access_level=access_level)

        # 5. Get conversation history
        history = session_store.get_history(sid)
        # Only pass the last few turns to LLM (exclude the current message which we just added)
        recent_history = history[:-1][-10:]  # last 5 exchanges (10 messages)

        # 6. Call LLM
        with metrics.timer("llm_latency_ms"):
            llm_result = await llm_service.generate_response(
                user_message=user_message,
                session=session,
                rag_context=rag_context,
                conversation_history=recent_history,
            )
        metrics.increment("messages_processed")

        # 7. Handle tool calls if any
        if llm_result["tool_calls"]:
            metrics.increment("tool_calls_total", len(llm_result["tool_calls"]))
            response_text = await self._handle_tool_calls(
                llm_result["tool_calls"],
                session,
                db,
                recent_history + [{"role": "user", "content": user_message}],
            )
        else:
            response_text = llm_result["response"]

        # 8. Apply safety guardrails to response
        response_text = check_response_safety(
            response_text,
            session.get("user_type", "guest"),
        )

        # 9. Add assistant response to history
        session_store.add_message(sid, "assistant", response_text)

        return {
            "reply": response_text,
            "session_id": sid,
            "user_type": session.get("user_type", "guest"),
            "verified": session.get("verified", False),
        }

    async def _handle_tool_calls(
        self,
        tool_calls: list,
        session: dict,
        db: Session,
        conversation_history: list,
    ) -> str:
        """Execute tool calls and get the final LLM response with results."""
        all_results = []

        for tc in tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            logger.info(f"Executing tool: {tool_name} with args: {json.dumps(tool_args)}")

            # Execute via tool router
            with metrics.timer(f"tool_{tool_name}_ms"):
                result = tool_router.execute(tool_name, tool_args, session, db)
            all_results.append((tool_name, result))

            logger.info(f"Tool result: {json.dumps(result, default=str)[:200]}...")

        # Send tool results back to LLM for natural language response
        # Use the last tool call's result for the response
        if all_results:
            last_tool_name, last_result = all_results[-1]
            response = await llm_service.generate_with_tool_result(
                conversation_history=conversation_history,
                tool_name=last_tool_name,
                tool_result=last_result,
            )
            return response

        return "I tried to process your request but encountered an issue. Please try again."


# Global orchestrator instance
orchestrator = Orchestrator()
