import re
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from config import Config


def extract_record_number(text: str) -> Optional[str]:
    match = re.search(r"\b(INC|REQ|CHG|TASK)\d{6,}\b", text.upper())
    return match.group(0) if match else None


def normalize_servicenow_state(state_value):
    state_map = {
        "1": "New",
        "2": "In Progress",
        "3": "On Hold",
        "6": "Resolved",
        "7": "Closed",
        "8": "Canceled"
    }

    if state_value is None:
        return None

    return state_map.get(str(state_value), str(state_value))


async def get_servicenow_record(
    record_number: Optional[str] = None,
    query_text: Optional[str] = None
) -> Dict[str, Any]:
    try:
        if not Config.SERVICENOW_INSTANCE:
            return {
                "success": False,
                "error": "ServiceNow instance is not configured."
            }

        async with httpx.AsyncClient(timeout=20) as client:
            if record_number:
                url = f"{Config.SERVICENOW_INSTANCE}/api/now/table/incident"

                params = {
                    "sysparm_query": f"number={record_number}",
                    "sysparm_limit": "1",
                    "sysparm_fields": (
                        "number,short_description,state,priority,"
                        "assignment_group,assigned_to,opened_at,updated_on,close_notes"
                    )
                }

                response = await client.get(
                    url,
                    params=params,
                    auth=(Config.SERVICENOW_USERNAME, Config.SERVICENOW_PASSWORD),
                    headers={"Accept": "application/json"}
                )

                response.raise_for_status()

                records = response.json().get("result", [])

                if not records:
                    return {
                        "success": True,
                        "found": False,
                        "message": f"No ServiceNow record found for {record_number}"
                    }

                record = records[0]

                record["state_display"] = normalize_servicenow_state(
                    record.get("state")
                )

                return {
                    "success": True,
                    "found": True,
                    "record": record
                }

            if query_text:
                url = f"{Config.SERVICENOW_INSTANCE}/api/now/table/incident"

                params = {
                    "sysparm_query": f"short_descriptionLIKE{query_text}",
                    "sysparm_limit": "5",
                    "sysparm_fields": (
                        "number,short_description,state,priority,"
                        "assignment_group,assigned_to,opened_at,updated_on"
                    )
                }

                response = await client.get(
                    url,
                    params=params,
                    auth=(Config.SERVICENOW_USERNAME, Config.SERVICENOW_PASSWORD),
                    headers={"Accept": "application/json"}
                )

                response.raise_for_status()

                records = response.json().get("result", [])

                for record in records:
                    record["state_display"] = normalize_servicenow_state(
                        record.get("state")
                    )

                return {
                    "success": True,
                    "found": len(records) > 0,
                    "records": records
                }

        return {
            "success": False,
            "error": "No ServiceNow record number or query text provided."
        }

    except Exception as e:
        logger.exception("ServiceNow lookup failed")
        return {
            "success": False,
            "error": str(e)
        }
