from __future__ import annotations

import asyncio
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import litellm
from crewai import Crew, Task, Process
from crewai.llm import LLM

# Automatically retry and backoff when Groq rate limits (429) occur
litellm.num_retries = 3
litellm.retry_delay = 3

from agents.researcher import create_researcher_agent
from agents.writer import create_writer_agent
from agents.budget_agent import create_budget_agent
from agents.hotel_agent import create_hotel_agent
from core.config import get_settings
from core.logger import get_logger
from models.request import TravelRequest

logger = get_logger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

_CREW_OUTPUT_INSTRUCTIONS = (
    "You MUST respond ONLY with valid JSON. No markdown, no code fences, "
    "no explanations. Just raw JSON."
)


def _build_crew(request: TravelRequest) -> Crew:
    """Assemble the CrewAI crew with all agents and tasks."""
    settings = get_settings()

    # Expose GROQ_API_KEY to os.environ so LiteLLM (used by CrewAI) can find it
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
    os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
    os.environ["OTEL_SDK_DISABLED"] = "true"

    # Distribute specialized agents across distinct Groq model buckets.
    # On Groq on-demand, each model architecture has a separate 8,000 TPM limit.
    # Alternating 20b and 120b guarantees we never hit the rate limit!
    researcher_llm = "groq/openai/gpt-oss-20b"
    writer_llm = "groq/openai/gpt-oss-120b"
    budget_llm = "groq/openai/gpt-oss-20b"
    hotel_llm = "groq/openai/gpt-oss-120b"

    researcher = create_researcher_agent(researcher_llm)
    writer = create_writer_agent(writer_llm)
    budget = create_budget_agent(budget_llm)
    hotel = create_hotel_agent(hotel_llm)

    prefs = ", ".join(request.preferences) if request.preferences else "general"

    research_task = Task(
        description=(
            f"Research the top attractions, cultural experiences, local cuisines, "
            f"and hidden gems in {request.destination} for a {request.days}-day trip. "
            f"Traveler preferences: {prefs}. Budget: {request.budget}.\n\n"
            f"{_CREW_OUTPUT_INSTRUCTIONS}\n"
            f"Return JSON with keys: 'places' (list of strings), "
            f"'activities' (list of strings), 'tips' (list of strings)."
        ),
        expected_output="A JSON object with 'places', 'activities', and 'tips' arrays.",
        agent=researcher,
    )

    itinerary_task = Task(
        description=(
            f"Using the research findings, create a detailed {request.days}-day "
            f"itinerary for {request.destination}. Preferences: {prefs}.\n\n"
            f"{_CREW_OUTPUT_INSTRUCTIONS}\n"
            f"Return JSON with key 'itinerary' — an array of objects, each with "
            f"'day' (int), 'title' (string), and 'activities' (list of strings)."
        ),
        expected_output="A JSON object with an 'itinerary' array of day objects.",
        agent=writer,
        context=[research_task],
    )

    budget_task = Task(
        description=(
            f"Estimate a realistic budget breakdown for a {request.days}-day trip "
            f"to {request.destination}. Target budget: {request.budget}. "
            f"Preferences: {prefs}.\n\n"
            f"{_CREW_OUTPUT_INSTRUCTIONS}\n"
            f"Return JSON with key 'budget_estimate' (string summary, e.g. "
            f"'$2,500 - $3,200 total: Accommodation $800-1000, Food $400-600, "
            f"Activities $300-500, Transport $200-300, Misc $100-200')."
        ),
        expected_output="A JSON object with a 'budget_estimate' string.",
        agent=budget,
        context=[],
    )

    hotel_task = Task(
        description=(
            f"Recommend 3-5 hotels in {request.destination} for a {request.days}-day "
            f"stay. Budget: {request.budget}. Preferences: {prefs}.\n\n"
            f"{_CREW_OUTPUT_INSTRUCTIONS}\n"
            f"Return JSON with key 'hotels' — an array of objects, each with "
            f"'name' (string), 'category' (string), 'price_range' (string), "
            f"and 'highlights' (list of strings)."
        ),
        expected_output="A JSON object with a 'hotels' array.",
        agent=hotel,
        context=[],
    )

    crew = Crew(
        agents=[researcher, writer, budget, hotel],
        tasks=[research_task, itinerary_task, budget_task, hotel_task],
        process=Process.sequential,
        verbose=False,
    )

    return crew


def _run_crew_sync(request: TravelRequest) -> dict:
    """Synchronous crew execution (called inside a thread)."""
    crew = _build_crew(request)
    logger.info("Starting CrewAI execution for destination=%s", request.destination)

    result = crew.kickoff(
        inputs={
            "destination": request.destination,
            "days": request.days,
            "budget": request.budget,
            "preferences": ", ".join(request.preferences),
        }
    )

    raw_output = result.raw if hasattr(result, "raw") else str(result)
    logger.info("CrewAI execution complete (%d chars output)", len(raw_output))

    # CrewAI sequential process returns the last task's output in result.raw.
    # We collect and merge valid outputs from each individual task.
    merged: dict = {}
    for task in crew.tasks:
        if hasattr(task, "output") and task.output:
            task_raw = task.output.raw if hasattr(task.output, "raw") else str(task.output)
            parsed = _parse_crew_output(task_raw)
            for k, v in parsed.items():
                if v:
                    merged[k] = v

    if not merged:
        merged = _parse_crew_output(raw_output)

    logger.info("Merged crew data keys: %s", list(merged.keys()))
    return merged


def _parse_crew_output(raw: str) -> dict:
    """Best-effort JSON extraction from crew output."""
    if not raw or not isinstance(raw, str):
        return {}

    clean_raw = raw.strip()
    if clean_raw.startswith("```"):
        clean_raw = re.sub(r"^```[a-zA-Z]*\n?", "", clean_raw)
        clean_raw = re.sub(r"```$", "", clean_raw).strip()

    # 1. Direct JSON parse
    try:
        val = json.loads(clean_raw)
        if isinstance(val, dict):
            return val
        elif isinstance(val, list):
            if val and isinstance(val[0], dict) and "day" in val[0]:
                return {"itinerary": val}
            elif val and isinstance(val[0], dict) and "name" in val[0]:
                return {"hotels": val}
            return {"items": val}
    except json.JSONDecodeError:
        pass

    # 2. Extract outermost dictionary { ... }
    first_brace = clean_raw.find("{")
    last_brace = clean_raw.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        try:
            val = json.loads(clean_raw[first_brace : last_brace + 1])
            if isinstance(val, dict):
                return val
        except json.JSONDecodeError:
            pass

    # 3. Extract outermost array [ ... ]
    first_bracket = clean_raw.find("[")
    last_bracket = clean_raw.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        try:
            val = json.loads(clean_raw[first_bracket : last_bracket + 1])
            if isinstance(val, list):
                if val and isinstance(val[0], dict) and "day" in val[0]:
                    return {"itinerary": val}
                elif val and isinstance(val[0], dict) and "name" in val[0]:
                    return {"hotels": val}
        except json.JSONDecodeError:
            pass

    # Fallback: if text contains budget-like or general text
    logger.warning("Could not parse JSON from crew output: %s", clean_raw[:150])
    return {
        "budget_estimate": clean_raw[:500] if clean_raw else "Budget estimate unavailable",
    }


async def run_crew(request: TravelRequest) -> dict:
    """Run the CrewAI crew asynchronously (offloaded to a thread pool).

    CrewAI's kickoff() is synchronous, so we avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, partial(_run_crew_sync, request))
