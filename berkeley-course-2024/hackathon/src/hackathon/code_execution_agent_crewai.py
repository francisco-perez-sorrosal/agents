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


filename = "2405.14831v1.pdf"


# @tool
# def read_file(file :str = "2405.14831v1.pdf"):
#     document_structure_file = f"{filename.rsplit(".", 1)[0]}_document_structure.pkl"

entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
code_generator_role: Role = entity_master.get_role("code_generator")

logger.info("================================================================================")
# logger.info(f"Code Generator Role:\n{pprint(code_generator_role)}")
logger.info("================================================================================")

code_executor_agent: Agent = code_generator_role.to_crewai_agent(verbose=True, allow_delegation=False, allow_code_execution=True)
code_execution_task = code_generator_role.get_crew_ai_task("user_task", code_executor_agent)

crew = Crew(
    agents=[code_executor_agent], 
    tasks=[code_execution_task],
    process=Process.sequential, # Sequential task execution
    
    
)

# Kick off the process with the Python problem as input
result = crew.kickoff(inputs={
    'user_coding_task': f"Read the file {filename.rsplit(".", 1)[0]}_document_structure.pkl. Just reply with the content of the file.",
    'output_type': 'output_only',
    },)

# logger.info(result)


logger.info("---------")

file_content = json.loads(json.dumps(result.raw))
logger.info(file_content)
logger.info(type(file_content))


