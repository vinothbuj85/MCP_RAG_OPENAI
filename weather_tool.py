import httpx
from typing import Dict, Any
from loguru import logger

from config import Config


async def get_current_weather(location: str) -> Dict[str, Any]:
    try:
        if not Config.WEATHER_API_KEY:
            return {
                "success": False,
                "error": "Weather API key is not configured."
            }

        params = {
            "q": location,
            "appid": Config.WEATHER_API_KEY,
            "units": "metric"
        }

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                Config.WEATHER_BASE_URL,
                params=params
            )

        response.raise_for_status()

        payload = response.json()

        return {
            "success": True,
            "location": payload.get("name"),
            "country": payload.get("sys", {}).get("country"),
            "temperature_c": payload.get("main", {}).get("temp"),
            "feels_like_c": payload.get("main", {}).get("feels_like"),
            "humidity": payload.get("main", {}).get("humidity"),
            "description": payload.get("weather", [{}])[0].get("description"),
            "wind_speed": payload.get("wind", {}).get("speed")
        }

    except Exception as e:
        logger.exception("Weather lookup failed")
        return {
            "success": False,
            "error": str(e)
        }
