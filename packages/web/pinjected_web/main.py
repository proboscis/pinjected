"""FastAPI backend for the pinjected web UI."""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional

from pinjected_web.services.graph_service import DIGraphService
from pinjected_web.models.graph_models import GraphResponse, NodeDetails, SearchResponse

app = FastAPI(title="Pinjected DI Visualization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph_service = DIGraphService()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Pinjected DI Visualization API"}


@app.get("/api/graph/{module_path}", response_model=GraphResponse)
async def get_graph(module_path: str, root_key: Optional[str] = None):
    """
    Get the dependency graph for a module path.
    
    Args:
        module_path: The module path to load
        root_key: Optional root key to filter the graph
        
    Returns:
        GraphResponse: The dependency graph data
    """
    try:
        return graph_service.get_graph(module_path, root_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/node/{module_path}/{node_key}", response_model=NodeDetails)
async def get_node_details(module_path: str, node_key: str):
    """
    Get detailed information about a specific node.
    
    Args:
        module_path: The module path to load
        node_key: The key of the node to get details for
        
    Returns:
        NodeDetails: Detailed information about the node
    """
    try:
        return graph_service.get_node_details(module_path, node_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/search/{module_path}", response_model=SearchResponse)
async def search(module_path: str, query: str = Query(...)):
    """
    Search for dependencies in a module.
    
    Args:
        module_path: The module path to load
        query: The search query
        
    Returns:
        SearchResponse: The search results
    """
    try:
        return graph_service.search(module_path, query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def start():
    """Start the FastAPI server."""
    uvicorn.run("pinjected_web.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
