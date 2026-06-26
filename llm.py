import json
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

from config import Config

client = OpenAI(api_key=Config.OPENAI_API_KEY)


def load_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def safe_json_loads(content: str) -> dict:
    try:
        return json.loads(content)
    except Exception:
        logger.error(f"Failed to parse JSON from LLM: {content}")
        return {
            "intent": "general",
            "use_servicenow": False,
            "use_weather": False,
            "use_rag": False,
            "servicenow_query": {
                "record_number": None,
                "query_text": None
            },
            "weather_query": {
                "location": None
            },
            "rag_query": None,
            "reason": "Fallback because router returned invalid JSON."
        }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def detect_intent(user_message: str) -> dict:
    router_prompt = load_prompt("prompts/router_prompt.txt")

    response = client.chat.completions.create(
        model=Config.OPENAI_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": router_prompt},
            {"role": "user", "content": user_message}
        ]
    )

    content = response.choices[0].message.content
    return safe_json_loads(content)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def generate_final_answer(
    user_message: str,
    router_decision: dict,
    servicenow_result=None,
    weather_result=None,
    rag_results=None
) -> str:
    final_prompt = load_prompt("prompts/final_answer_prompt.txt")

    payload = {
        "user_question": user_message,
        "router_decision": router_decision,
        "servicenow_result": servicenow_result,
        "weather_result": weather_result,
        "rag_results": rag_results
    }

    response = client.chat.completions.create(
        model=Config.OPENAI_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": final_prompt},
            {
                "role": "user",
                "content": json.dumps(payload, indent=2, ensure_ascii=False)
            }
        ]
    )

    return response.choices[0].message.content
