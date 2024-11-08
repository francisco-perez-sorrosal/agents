import asyncio
import os

from datetime import datetime
from rich import print, print_json
from typing import Type
from utils import edges_to_facts_string

from crewai import Agent, Task, Crew, Process
from crewai.crews import CrewOutput
from crewai_tools import BaseTool
from graphiti_core.nodes import EpisodeType
from hackathon.graph_neo4j import clean_db
from hackathon.utils import Neo4jClientFactory
from llm_foundation.agent_types import Persona
from llm_foundation import logger
from pydantic import BaseModel, Field


# Initialize Graphiti client with Neo4j settings
neo4j_factory = Neo4jClientFactory()
graphiti_client = neo4j_factory.graphiti_client()
    
# Define the custom tool using Pydantic
class GraphitiSearchToolInput(BaseModel):
    """Input schema for GraphitiSearchTool."""
    query: str = Field(..., description="Search query")


class GraphitiSearchTool(BaseTool):
    name: str = "GraphitiSearch"
    description: str = "Searches the Graphiti graph database using the provided query."
    args_schema: Type[BaseModel] = GraphitiSearchToolInput

    async def _arun(self, query: str) -> str:
        edge_results = await graphiti_client.search(
            query,
            num_results=5)
        return edges_to_facts_string(edge_results)

    def _run(self, query: str) -> str:
        return asyncio.run(self._arun(query))


# Build indexes
async def build_indexes():
    await graphiti_client.build_indices_and_constraints()    

async def add_episodes(episodes):
    for i, episode in enumerate(episodes):
        await graphiti_client.add_episode(
            name=f"Life Meaning {i}",
            episode_body=episode,
            source=EpisodeType.text,
            source_description="life facts",
            reference_time=datetime.now()
        )

async def graph_creation_with_graphiti():
    logger.info("Clean old data")
    clean_db(neo4j_factory)
    logger.info("Building indexes")
    await build_indexes()
    # Add episodes
    episodes = [
        "The meaning of life is a good red wine.",
        "Fran thinks the meaning of life is to be happy.",
        "The meaning of life is make others happy.",
    ]    
    await add_episodes(episodes)
    logger.info(f"Graph Created")


def  main(create_graph: bool = False):
    
    if create_graph:
        asyncio.run(graph_creation_with_graphiti())
        
    logger.info(f"Current workding dir: {os.getcwd()}")

    # Agent Definition
    research_assistant = Persona.from_yaml_file("nf/src/ResearchMasterCrewAI.yaml")
    research_assistant_role = research_assistant.get_role("research_assistant")

    search_agent: Agent = research_assistant_role.to_crewai_agent(
        allow_delegation=False,
        tools=[GraphitiSearchTool()],
        verbose=True)

    search_task = Task(
        description=research_assistant_role.tasks[0].description,
        expected_output=research_assistant_role.tasks[0].expected_output,
        agent=search_agent,
    )

    # Create Crew with memory enabled
    crew = Crew(
        agents=[search_agent],
        tasks=[search_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Calling Agents ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    result: CrewOutput = crew.kickoff(inputs={"query": "What is the meaning of life?"})
    logger.info(".................................................................................")
    logger.info(f"Answer:\n{print(result.raw)}")
    logger.info(".................................................................................")


# Change to True to create graph in Neo4j if it does not exist
main(create_graph=False)
