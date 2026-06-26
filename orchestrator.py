import asyncio
from typing import Dict, Any, List
from loguru import logger

from llm import detect_intent, generate_final_answer
from rag import search_kb
from servicenow_tool import get_servicenow_record, extract_record_number
from weather_tool import get_current_weather


async def handle_user_message(user_message: str) -> Dict[str, Any]:
    router_decision = detect_intent(user_message)

    logger.info(f"Router decision: {router_decision}")

    used_tools: List[str] = []
    sources: List[Dict[str, Any]] = []

    servicenow_result = None
    weather_result = None
    rag_results = None

    tasks = {}

    # ServiceNow
    if router_decision.get("use_servicenow"):
        sn_query = router_decision.get("servicenow_query", {}) or {}

        record_number = sn_query.get("record_number")
        query_text = sn_query.get("query_text")

        if not record_number:
            record_number = extract_record_number(user_message)

        tasks["servicenow"] = get_servicenow_record(
            record_number=record_number,
            query_text=query_text
        )

    # Weather
    if router_decision.get("use_weather"):
        weather_query = router_decision.get("weather_query", {}) or {}
        location = weather_query.get("location")

        if location:
            tasks["weather"] = get_current_weather(location)
        else:
            weather_result = {
                "success": False,
                "error": "No weather location was provided."
            }

    # Execute live tools in parallel
    if tasks:
        results = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )

        for tool_name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                result = {
                    "success": False,
                    "error": str(result)
                }

            if tool_name == "servicenow":
                servicenow_result = result
                used_tools.append("servicenow")

            elif tool_name == "weather":
                weather_result = result
                used_tools.append("weather")

    # RAG search
    if router_decision.get("use_rag"):
        rag_query = router_decision.get("rag_query") or user_message

        try:
            rag_results = search_kb(rag_query, top_k=5)
            used_tools.append("rag")

            for item in rag_results:
                sources.append(
                    {
                        "title": item.get("title"),
                        "source": item.get("source"),
                        "score": item.get("score")
                    }
                )

        except Exception as e:
            logger.exception("RAG lookup failed")
            rag_results = [
                {
                    "success": False,
                    "error": str(e)
                }
            ]

    final_answer = generate_final_answer(
        user_message=user_message,
        router_decision=router_decision,
        servicenow_result=servicenow_result,
        weather_result=weather_result,
        rag_results=rag_results
    )

    return {
        "answer": final_answer,
        "intent": router_decision.get("intent", "general"),
        "used_tools": used_tools,
        "sources": sources,
        "router_decision": router_decision
    }
