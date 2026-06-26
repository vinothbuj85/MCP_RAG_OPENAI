from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    user_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    message: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    used_tools: List[str]
    sources: List[Dict[str, Any]] = []
