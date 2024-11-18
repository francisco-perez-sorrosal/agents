import asyncio

from typing import Any, Dict, List, Literal, Optional, Type

from crewai import Agent, Task, Crew, Process
from crewai.crews import CrewOutput
from crewai_tools import BaseTool
from graphiti_core.edges import EntityEdge
from pydantic import BaseModel, Field

from hackathon.utils import Neo4jClientFactory


def edges_to_facts_string(entities: list[EntityEdge]):
    """Funcion that converts the edge results into a readable string format"""
    return '\n'.join([f"- {edge.fact}" for edge in entities])


class GraphitiSearchToolInput(BaseModel):
    """Input schema for GraphitiSearchTool."""
    query: str = Field(..., description="Search query")


class GraphitiSearchTool(BaseTool):
    name: str = "GraphitiSearch"
    description: str = "Searches the Graphiti graph database using the provided query."
    args_schema: Type[BaseModel] = GraphitiSearchToolInput

    async def _arun(self, query: str) -> str:
        neo4j_factory = Neo4jClientFactory()
        graphiti_client = neo4j_factory.graphiti_client()
        edge_results = await graphiti_client.search(
            query,
            num_results=5)
        return edges_to_facts_string(edge_results)

    def _run(self, query: str) -> str:
        return asyncio.run(self._arun(query))
