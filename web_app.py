"""Small web UI proxy for the A2A legal multi-agent demo."""

from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv(override=True)

CUSTOMER_AGENT_URL = os.getenv("CUSTOMER_AGENT_URL", "http://localhost:10100")
ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Legal Multi-Agent Web UI")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    latency_seconds: float


def _extract_text(response: object) -> str:
    result_text = ""
    if hasattr(response, "root"):
        root = response.root
        if hasattr(root, "result"):
            result = root.result
            if hasattr(result, "artifacts") and result.artifacts:
                for artifact in result.artifacts:
                    for part in artifact.parts:
                        p = part.root if hasattr(part, "root") else part
                        if hasattr(p, "text"):
                            result_text += p.text
            elif hasattr(result, "parts") and result.parts:
                for part in result.parts:
                    p = part.root if hasattr(part, "root") else part
                    if hasattr(p, "text"):
                        result_text += p.text
    return result_text


async def _ask_customer_agent(question: str) -> AskResponse:
    async with httpx.AsyncClient(timeout=300.0) as http_client:
        card_url = f"{CUSTOMER_AGENT_URL}/.well-known/agent.json"
        try:
            card_resp = await http_client.get(card_url)
            card_resp.raise_for_status()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Customer Agent is not reachable. Start Stage 5 with start_all.ps1 first.",
            ) from exc

        from a2a.client import A2AClient
        from a2a.types import AgentCard, Message, Part, Role, SendMessageRequest, TextPart
        from a2a.types import MessageSendParams as MSP

        agent_card = AgentCard.model_validate(card_resp.json())
        client = A2AClient(httpx_client=http_client, agent_card=agent_card)
        message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=question))],
            message_id=str(uuid4()),
        )
        request = SendMessageRequest(id=str(uuid4()), params=MSP(message=message))

        started_at = time.perf_counter()
        response = await client.send_message(request)
        latency_seconds = time.perf_counter() - started_at

    answer = _extract_text(response)
    if not answer:
        answer = "No text response received from the agent."
    return AskResponse(answer=answer, latency_seconds=latency_seconds)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/status")
async def status() -> dict[str, object]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{CUSTOMER_AGENT_URL}/.well-known/agent.json")
            response.raise_for_status()
            card = response.json()
            return {
                "ok": True,
                "customer_agent_url": CUSTOMER_AGENT_URL,
                "agent_name": card.get("name"),
                "version": card.get("version"),
            }
        except Exception as exc:
            return {
                "ok": False,
                "customer_agent_url": CUSTOMER_AGENT_URL,
                "error": str(exc),
            }


@app.post("/api/ask", response_model=AskResponse)
async def ask(payload: AskRequest) -> AskResponse:
    return await _ask_customer_agent(payload.question.strip())
