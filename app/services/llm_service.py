import json
import asyncio
import time
from typing import Optional, List
import google.generativeai as genai
from app.config import settings


# ── System Prompt ────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful, professional, and friendly AI assistant for **City General Hospital (CGH)**.
Your name is **CGH Assistant**.

## Your Role
- Help callers with hospital information, appointment booking, doctor lookups, report status, and billing queries.
- You handle two types of users:
  - **Guest users**: Can only ask general questions (timings, departments, directions, insurance info).
  - **Registered/verified users**: Can access personalized services (appointments, reports, billing).

## Rules (MUST FOLLOW)
1. **NEVER provide medical advice, diagnoses, or treatment recommendations.** If asked, politely decline and suggest visiting the hospital or calling the emergency number.
2. **NEVER fabricate information.** Only use the provided FAQ context and tool results to answer questions.
3. If the FAQ context contains relevant information, use it to answer. Always be accurate.
4. If a guest user asks for personalized services (appointments, reports, billing), tell them they need to **login first** by providing their registered phone number.
5. For registered users, use the available tools to fulfill their requests.
6. Be conversational, warm, and concise. Use short paragraphs.
7. When listing information (doctors, timings), format it clearly.
8. If you're unsure about something, say so honestly and suggest contacting the hospital directly.
9. Always end with a helpful follow-up like "Is there anything else I can help you with?"

## Available Tools
You have access to these tools for REGISTERED users:
- `search_doctors`: Search for doctors by department, name, or specialization
- `book_appointment`: Book an appointment with a doctor
- `cancel_appointment`: Cancel an existing appointment
- `list_appointments`: List a patient's upcoming appointments
- `check_report_status`: Check lab report status for a patient
- `get_billing_summary`: Get billing information for a patient

Tools available for ALL users (including guests):
- `get_department_info`: Get information about hospital departments

## Context
Current user status will be provided in each message. Use tools only when appropriate.
"""


# ── Tool Declarations for Gemini ─────────────────────

TOOL_DECLARATIONS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="search_doctors",
                description="Search for doctors at the hospital. Can filter by department name, doctor name, or specialization. At least one parameter should be provided.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "department": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Department name to filter by (e.g., 'Cardiology', 'Pediatrics')",
                        ),
                        "name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Doctor name or partial name to search for",
                        ),
                        "specialization": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Specialization to search for (e.g., 'Joint Replacement')",
                        ),
                    },
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="get_department_info",
                description="Get information about a specific hospital department including timings, floor, and services. Available to all users.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "department_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Name of the department (e.g., 'Cardiology')",
                        ),
                    },
                    required=["department_name"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="book_appointment",
                description="Book an appointment with a doctor for the verified patient. Requires login.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "doctor_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Full name of the doctor (e.g., 'Dr. Ananya Sharma')",
                        ),
                        "date": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Appointment date in YYYY-MM-DD format",
                        ),
                        "time_slot": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Preferred time slot (e.g., '10:00 AM', '2:30 PM')",
                        ),
                        "reason": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Reason for the appointment",
                        ),
                    },
                    required=["doctor_name", "date", "time_slot"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="cancel_appointment",
                description="Cancel an existing appointment for the verified patient. Requires login.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "appointment_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="ID of the appointment to cancel",
                        ),
                    },
                    required=["appointment_id"],
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="list_appointments",
                description="List all upcoming appointments for the verified patient. Requires login.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={},
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="check_report_status",
                description="Check the status of lab reports for the verified patient. Requires login.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={},
                ),
            ),
            genai.protos.FunctionDeclaration(
                name="get_billing_summary",
                description="Get billing summary and outstanding amounts for the verified patient. Requires login.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={},
                ),
            ),
        ]
    )
]


class LLMService:
    """Gemini LLM integration with tool calling support."""

    def __init__(self):
        self._model = None
        self._initialized = False

    def initialize(self):
        """Initialize the Gemini model."""
        if self._initialized:
            return

        if not settings.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY not set! LLM service will not work.")
            return

        genai.configure(api_key=settings.GEMINI_API_KEY)

        self._model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            tools=TOOL_DECLARATIONS,
        )
        self._initialized = True
        print(f"LLM service initialized with model: {settings.GEMINI_MODEL}")

    def build_context_message(
        self,
        user_message: str,
        session: dict,
        rag_context: List[dict],
    ) -> str:
        """Build the full context message to send to the LLM."""
        parts = []

        # User status context
        user_type = session.get("user_type", "guest")
        if user_type == "registered" and session.get("verified"):
            parts.append(
                f"[SYSTEM CONTEXT] User is VERIFIED as: {session.get('patient_name')} "
                f"(Patient ID: {session.get('patient_id')}, Code: {session.get('patient_code')}). "
                f"They can use all tools."
            )
        else:
            parts.append(
                "[SYSTEM CONTEXT] User is a GUEST (not logged in). "
                "They can only ask general questions. For personalized services, "
                "ask them to login using the login button with their registered phone number."
            )

        # RAG context
        if rag_context:
            parts.append("\n[HOSPITAL KNOWLEDGE BASE - Use this to answer questions]")
            for i, ctx in enumerate(rag_context, 1):
                parts.append(f"Source: {ctx['source']} (relevance: {ctx['score']})")
                parts.append(ctx["content"])
                parts.append("---")

        # User's actual message
        parts.append(f"\n[USER MESSAGE] {user_message}")

        return "\n".join(parts)

    async def generate_response(
        self,
        user_message: str,
        session: dict,
        rag_context: List[dict],
        conversation_history: List[dict],
    ) -> dict:
        """
        Generate a response from Gemini.

        Returns:
            {
                "response": str,           # The text response
                "tool_calls": list[dict],   # Any tool calls requested
            }
        """
        if not self._initialized or not self._model:
            return {
                "response": "I'm sorry, the AI service is not available right now. "
                            "Please try again later or call +91-11-2345-6789 for assistance.",
                "tool_calls": [],
            }

        # Build conversation for Gemini
        gemini_history = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # Create chat session with history
        chat = self._model.start_chat(history=gemini_history)

        # Build the context-enriched message
        context_message = self.build_context_message(user_message, session, rag_context)

        loop = asyncio.get_event_loop()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Run synchronous Gemini call in executor to avoid blocking async loop
                response = await loop.run_in_executor(
                    None, chat.send_message, context_message
                )

                # Check for tool calls
                tool_calls = []
                response_text = ""

                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if part.function_call:
                            fc = part.function_call
                            tool_calls.append({
                                "name": fc.name,
                                "args": dict(fc.args) if fc.args else {},
                            })
                        elif part.text:
                            response_text += part.text

                return {
                    "response": response_text,
                    "tool_calls": tool_calls,
                }

            except Exception as e:
                error_str = str(e).lower()
                print(f"LLM Error (attempt {attempt + 1}/{max_retries}): {e}")

                # Retry on rate limit / quota / resource errors
                if attempt < max_retries - 1 and any(
                    keyword in error_str
                    for keyword in ["429", "rate", "quota", "resource", "exhausted", "limit"]
                ):
                    wait_time = (attempt + 1) * 10  # 10s, 20s
                    print(f"  Rate limited — retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                return {
                    "response": "I encountered an issue processing your request. "
                                "Please try again or call our helpline at +91-11-2345-6789.",
                    "tool_calls": [],
                }

    async def generate_with_tool_result(
        self,
        conversation_history: List[dict],
        tool_name: str,
        tool_result: dict,
    ) -> str:
        """
        Send tool result back to Gemini and get the final natural language response.
        """
        if not self._initialized or not self._model:
            return "Service temporarily unavailable."

        # Rebuild chat with history
        gemini_history = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        chat = self._model.start_chat(history=gemini_history)

        try:
            loop = asyncio.get_event_loop()

            # Build the function response content
            tool_response_content = genai.protos.Content(
                parts=[
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": tool_result},
                        )
                    )
                ]
            )

            # Run synchronous Gemini call in executor
            response = await loop.run_in_executor(
                None, chat.send_message, tool_response_content
            )

            # Extract text response
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.text:
                        return part.text

            return "I processed your request but couldn't generate a response. Please try again."

        except Exception as e:
            print(f"LLM Error (tool result): {e}")
            return f"I got the result but had trouble formatting the response. Here's the raw data: {json.dumps(tool_result, indent=2)}"


# Global LLM service instance
llm_service = LLMService()
