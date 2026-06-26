import re
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from config import Config


def extract_record_number(text: str) -> Optional[str]:
    """
    Extract ServiceNow record number from user text.
    Supports INC, REQ, RITM, CHG, TASK.
    """
    match = re.search(r"\b(INC|REQ|RITM|CHG|TASK)\d{6,}\b", text.upper())
    return match.group(0) if match else None


def get_table_for_record(record_number: str) -> str:
    """
    Map ServiceNow record prefix to correct ServiceNow table.
    """

    record_number = record_number.upper()

    if record_number.startswith("INC"):
        return "incident"

    if record_number.startswith("REQ"):
        return "sc_request"

    if record_number.startswith("RITM"):
        return "sc_req_item"

    if record_number.startswith("CHG"):
        return "change_request"

    if record_number.startswith("TASK"):
        return "task"

    return "task"


async def get_servicenow_record(
    record_number: Optional[str] = None,
    query_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get ServiceNow record from original/live ServiceNow instance.
    """

    try:
        if not Config.SERVICENOW_INSTANCE:
            return {
                "success": False,
                "error": "ServiceNow instance is not configured."
            }

        if not Config.SERVICENOW_USERNAME or not Config.SERVICENOW_PASSWORD:
            return {
                "success": False,
                "error": "ServiceNow username/password is not configured."
            }

        async with httpx.AsyncClient(timeout=20) as client:

            if record_number:
                table_name = get_table_for_record(record_number)

                url = f"{Config.SERVICENOW_INSTANCE}/api/now/table/{table_name}"

                params = {
                    "sysparm_query": f"number={record_number}",
                    "sysparm_limit": "1",
                    "sysparm_display_value": "true",
                    "sysparm_exclude_reference_link": "true",
                    "sysparm_fields": (
                        "number,"
                        "short_description,"
                        "description,"
                        "state,"
                        "priority,"
                        "assignment_group,"
                        "assigned_to,"
                        "opened_by,"
                        "opened_at,"
                        "sys_updated_on,"
                        "close_notes"
                    )
                }

                response = await client.get(
                    url,
                    params=params,
                    auth=(Config.SERVICENOW_USERNAME, Config.SERVICENOW_PASSWORD),
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()

                payload = response.json()
                records = payload.get("result", [])

                if not records:
                    return {
                        "success": True,
                        "found": False,
                        "table": table_name,
                        "record_number": record_number,
                        "message": f"No ServiceNow record found for {record_number}"
                    }

                return {
                    "success": True,
                    "found": True,
                    "table": table_name,
                    "record_number": record_number,
                    "record": records[0]
                }

            if query_text:
                url = f"{Config.SERVICENOW_INSTANCE}/api/now/table/incident"

                params = {
                    "sysparm_query": f"short_descriptionLIKE{query_text}",
                    "sysparm_limit": "5",
                    "sysparm_display_value": "true",
                    "sysparm_exclude_reference_link": "true",
                    "sysparm_fields": (
                        "number,"
                        "short_description,"
                        "state,"
                        "priority,"
                        "assignment_group,"
                        "assigned_to,"
                        "opened_at,"
                        "sys_updated_on"
                    )
                }

                response = await client.get(
                    url,
                    params=params,
                    auth=(Config.SERVICENOW_USERNAME, Config.SERVICENOW_PASSWORD),
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    }
                )

                response.raise_for_status()

                records = response.json().get("result", [])

                return {
                    "success": True,
                    "found": len(records) > 0,
                    "table": "incident",
                    "records": records
                }

        return {
            "success": False,
            "error": "No ServiceNow record number or query text provided."
        }

    except httpx.HTTPStatusError as e:
        logger.exception("ServiceNow HTTP error")

        return {
            "success": False,
            "error": "ServiceNow API returned an error.",
            "status_code": e.response.status_code,
            "details": e.response.text
        }

    except Exception as e:
        logger.exception("ServiceNow lookup failed")

        return {
            "success": False,
            "error": str(e)
        }
