import json
import pprint
import pickle
import hashlib

from typing import Dict, List
import numpy as np


from crewai import Agent, Task, Crew, Process
from crewai.crews import CrewOutput
from crewai_tools import tool
from llm_foundation.agent_types import Persona, Role, CrewAITask
from pydantic import BaseModel

from hackathon.tools import load_pdf, split_text

from llm_foundation import logger


document_name: str = "2405.14831v1.pdf"
document_structure_file = f"{document_name.rsplit(".", 1)[0]}_document_structure.pkl"


@tool
def read_file(filename:str = "2405.14831v1.pdf"):
    """Reads a file from disk.
    It returns the content of the file.
    """
    logger.info(f"Loading document structure from {filename}")
    return pickle.load(open(filename, "rb"))


entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
code_generator_role: Role = entity_master.get_role("file_reader")


file_reader_agent: Agent = code_generator_role.to_crewai_agent(verbose=True,
                                                               allow_delegation=False,
                                                               allow_code_execution=False,
                                                               tools=[read_file])
file_reader_task = code_generator_role.get_crew_ai_task("read_file", file_reader_agent, tools=[read_file])

crew = Crew(
    agents=[file_reader_agent], 
    tasks=[file_reader_task],
    # process=Process.sequential, # Sequential task execution
)

# Kick off the process with the Python problem as input
result = crew.kickoff(inputs={'filename': document_structure_file,},)

logger.info("---------")

file_content = json.loads(json.dumps(result.raw))
logger.info(file_content)
logger.info(type(file_content))
