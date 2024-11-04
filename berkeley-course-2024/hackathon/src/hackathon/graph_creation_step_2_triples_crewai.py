import json
import pprint
import pickle
import hashlib

from typing import Dict, List
import numpy as np


from crewai import Agent, Task, Crew, Process
from crewai.crews import CrewOutput
from llm_foundation.agent_types import Persona, Role, CrewAITask
from pydantic import BaseModel

from hackathon.tools import read_file, filter_named_entities, create_document_deduped_entities_dict
from hackathon.input_output_types import DocumentStructures, DocumentStructure, NamedEntities

from llm_foundation import logger


document_name: str = "2405.14831v1.pdf"
document_structure_file = f"{document_name.rsplit(".", 1)[0]}_document_structure.pkl"


entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
file_reader_role: Role = entity_master.get_role("file_reader")
entity_filter_role: Role = entity_master.get_role("entity_filter")
entity_deduper_role: Role = entity_master.get_role("entity_deduper")


file_reader_agent: Agent = file_reader_role.to_crewai_agent(verbose=True,
                                                               allow_delegation=False,
                                                               allow_code_execution=False,
                                                               tools=[read_file],)
file_reader_task = file_reader_role.get_crew_ai_task("read_file", 
                                                     file_reader_agent, 
                                                     tools=[read_file], #)
                                                     output_json=DocumentStructures,)

entity_filter_agent: Agent = entity_filter_role.to_crewai_agent(verbose=True,
                                                              allow_delegation=False,
                                                              allow_code_execution=False,
                                                              tools=[filter_named_entities])
filter_entities_task = entity_filter_role.get_crew_ai_task("filter_entities", 
                                                         entity_filter_agent, 
                                                         tools=[filter_named_entities], #)
                                                         output_json=DocumentStructures,)

entity_deduper_agent: Agent = entity_deduper_role.to_crewai_agent(verbose=True,
                                                              allow_delegation=False,
                                                              allow_code_execution=False,
                                                              tools=[create_document_deduped_entities_dict])

dedup_entities_task = entity_deduper_role.get_crew_ai_task("dedup_entities", 
                                                         entity_filter_agent, 
                                                         tools=[create_document_deduped_entities_dict], #)
                                                         output_json=NamedEntities,)


crew = Crew(
    agents=[file_reader_agent, entity_filter_agent, entity_deduper_agent], 
    tasks=[file_reader_task, filter_entities_task, dedup_entities_task],
    process=Process.sequential,  # Sequential task execution
)

# Kick off the process with the Python problem as input
crew_inputs = {'filename': document_structure_file,}
result: CrewOutput = crew.kickoff(inputs=crew_inputs,)

logger.info("---------------------------------------------------------------------------------")
file_content = json.loads(json.dumps(result.json))
logger.info(f"Output type: {type(file_content)}")
logger.info(file_content)
logger.info("---------------------------------------------------------------------------------")
