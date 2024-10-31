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


@tool
def filter_named_entities(document_structure_with_entities_and_triples: List[dict]) -> List[dict]:
    """Your function description here.

    Args:
        document_structure_with_entities_and_triples (List[dict]): A list of dictionaries containing 
        the document structure with entities and triples.

    Returns:
        List[dict]: A list of the named entities mentioned in the document.
    """
    for chunk_info in document_structure_with_entities_and_triples:
        named_entities = chunk_info["named_entities"]
        logger.info(named_entities)
        named_entities = [entity.lower() for entity in named_entities]
        triples = chunk_info["triples"]
        logger.info(f"Initial Named Entities ({len(named_entities)}): {named_entities}")
        named_entities: set = set(named_entities)
        logger.info(f"Initial Named Entities after dedup ({len(named_entities)}): {named_entities}")
        wrong_triples = 0
        for triple in triples:
            if len(triple) != 3:
                wrong_triples += 1
                continue
            named_entities.add(triple[0].lower())
            named_entities.add(triple[2].lower())
        logger.info(f"Final Named Entities ({len(named_entities)}): {named_entities}")
        chunk_info["named_entities"] = list(named_entities)
    return document_structure_with_entities_and_triples[:1] # TODO Remove this filter!!!! Just for testing


entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
file_reader_role: Role = entity_master.get_role("file_reader")
entity_filter_role: Role = entity_master.get_role("entity_filter")

class DocumentStructure(BaseModel):
    id: int
    text: str
    named_entities: List[str]
    triples: List[List[str]]
    
class DocumentStructures(BaseModel):    
    document_structures: List[DocumentStructure]

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

crew = Crew(
    agents=[file_reader_agent, entity_filter_agent], 
    tasks=[file_reader_task, filter_entities_task],
    process=Process.sequential,  # Sequential task execution
)

# Kick off the process with the Python problem as input
crew_inputs = {'filename': document_structure_file,}
result: CrewOutput = crew.kickoff(inputs=crew_inputs,)

logger.info("---------")

file_content = json.loads(json.dumps(result.json))
logger.info(file_content)
logger.info(type(file_content))
