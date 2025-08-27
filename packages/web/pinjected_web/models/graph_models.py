"""Models for the pinjected web API."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class Position(BaseModel):
    """Position of a node in the graph."""

    x: float
    y: float


class MetadataInfo(BaseModel):
    """Metadata information for a node."""

    location: Optional[Dict[str, Any]] = None
    docstring: Optional[str] = None
    source: Optional[str] = None


class NodeData(BaseModel):
    """Data for a node in the graph."""

    id: str
    position: Dict[str, float]
    data: Dict[str, Any]


class EdgeData(BaseModel):
    """Data for an edge in the graph."""

    id: str
    source: str
    target: str
    animated: bool = False


class GraphResponse(BaseModel):
    """Response for the graph API."""

    nodes: List[NodeData]
    edges: List[EdgeData]


class NodeDetails(BaseModel):
    """Detailed information about a node."""

    key: str
    dependencies: List[str]
    used_by: List[str]
    metadata: Optional[MetadataInfo] = None
    spec: Optional[str] = None
    source_code: Optional[str] = None


class SearchResponse(BaseModel):
    """Response for the search API."""

    results: List[str]
