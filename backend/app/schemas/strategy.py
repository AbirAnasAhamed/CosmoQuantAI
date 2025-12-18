from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union

class StrategyNode(BaseModel):
    id: str
    type: str  # 'TRIGGER', 'INDICATOR', 'CONDITION', 'ACTION'
    data: Dict[str, Any] = {}
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

class StrategyEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class VisualStrategyConfig(BaseModel):
    nodes: List[StrategyNode]
    edges: List[StrategyEdge]

class CompiledStrategy(BaseModel):
    source_code: str
    class_name: str
    config: VisualStrategyConfig
