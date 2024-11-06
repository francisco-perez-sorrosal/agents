import os
import asyncio
from typing import Type

from utils import edges_to_facts_string

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from graphiti_core import Graphiti

#Load the persona from YAML
from llm_foundation.agent_types import Persona

# Initialize Graphiti client with Neo4j settings
client = Graphiti(
    os.environ["NEO4J_URI"],
    os.environ["NEO4J_USERNAME"],
    os.environ["NEO4J_PASSWORD"])

research_assistant = Persona.from_yaml_file("ResearchMasterCrewAI.yaml")
research_assistant_role = research_assistant.get_role("research_assistant")

# Define the custom tool using Graphiti
class GraphitiSearchToolInput(BaseModel):
    """Input schema for GraphitiSearchTool."""
    query: str = Field(..., description="Search query")

class GraphitiSearchTool(BaseTool):
    name: str = "GraphitiSearch"
    description: str = "Searches the Graphiti graph database using the provided query."
    args_schema: Type[BaseModel] = GraphitiSearchToolInput

    async def _arun(self, query: str) -> str:
        edge_results = await client.search(
            query,
            num_results=5)
        return edges_to_facts_string(edge_results)

    def _run(self, query: str) -> str:
        return asyncio.run(self._arun(query))

search_agent = research_assistant_role.to_crewai_agent(
    tools=[GraphitiSearchTool()],
    allow_delegation=False,
    verbose=True)

search_task = research_assistant_role.get_crew_ai_task(
    "search_knowledge_graph",
    agent=search_agent)

# Create Crew with memory enabled
crew = Crew(
    agents=[search_agent],
    tasks=[search_task],
    process=Process.sequential,
    memory=True,  # Enable CrewAI's memory
    verbose=True,
    embedder={
        "provider": "openai",
        "config": {
            "model": 'text-embedding-ada-002'}})

