import json
import pprint
import pickle

from typing import Dict, List, Literal

from crewai import Agent, Task, Crew
from crewai.crews import CrewOutput
from llm_foundation import logger
from llm_foundation.agent_types import Persona, Role
from pydantic import BaseModel
from rich import print
from rich.pretty import pprint

from hackathon.tools import load_pdf, split_text

CHUNK_SIZE = 5000
document_name = "2405.14831v1.pdf"

def save_document_structure(document_chunks: List[dict], output_file: str, format: Literal["pickle", "json"] = "pickle"):
        logger.info(f"Saving document structure to {output_file}")
        match format:
            case "pickle":
                with open(output_file, "wb") as f:
                    pickle.dump(document_chunks, f)
            case "json":
                with open(output_file, "w") as f:
                    json.dump(document_chunks, f, indent=4)
            case _:
                raise ValueError(f"Invalid format: {format}")


def build_document_structure(document_path: str, chunk_size=1000) -> List[Dict]:
    text = load_pdf(document_path)
    chunks = split_text(text, chunk_size=chunk_size, char_overlap=0)
    document_chunks: List[Dict] = [ { "id":idx, "text":chunk.page_content } for idx, chunk in enumerate(chunks[0:1])]  # TODO Remove this [0:1] filter!!!! Just for testing
    assert len(document_chunks) == 1, f"Number of chunks mismatch: {len(document_chunks)} is not 1"  # TODO Remove this assert!!!! Just for testing
    logger.info("--------------------------------------------------------------------------------")
    logger.info(f"Number of chunks: {len(chunks)}")
    logger.info("--------------------------------------------------------------------------------")
    return document_chunks


########################################################################################
### Here starts everything...
########################################################################################

document_chunks = build_document_structure(document_name, chunk_size=CHUNK_SIZE)

entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
entity_extractor_role: Role = entity_master.get_role("entity_extractor")
triple_extractor_role: Role = entity_master.get_role("triple_extractor")

logger.info("================================================================================")
logger.info(f"Entity Extractor Role:\n{pprint(entity_extractor_role)}")
logger.info("================================================================================")

logger.info("================================================================================")
logger.info(f"Triple Extractor Role:\n{pprint(triple_extractor_role)}")
logger.info("================================================================================")

entity_extractor: Agent = entity_extractor_role.to_crewai_agent(verbose=True, allow_delegation=False)
triple_extractor: Agent = triple_extractor_role.to_crewai_agent(verbose=True, allow_delegation=False)

class ExtractedEntities(BaseModel):
    named_entities: List[str]

extract_entities = Task(
    description=entity_extractor_role.tasks[0].description,
    expected_output=entity_extractor_role.tasks[0].expected_output,
    agent=entity_extractor,
    output_json=ExtractedEntities,
)

class ExtractedTriples(BaseModel):
    named_entities: List[str]
    triples: List[List[str]]

extract_triples = Task(
    description=triple_extractor_role.tasks[0].description,
    expected_output=triple_extractor_role.tasks[0].expected_output,
    agent=triple_extractor,
    output_json=ExtractedTriples,
)

crew = Crew(
    agents=[entity_extractor, triple_extractor],
    tasks=[extract_entities, extract_triples],
    verbose=True,
)

def extend_document_chunks_with_entities_and_triples(document_chunks: List[Dict]) -> List[Dict]:

    for chunk in document_chunks:

        graph_creation_inputs = {
            "paragraph": chunk["text"],
            "entity_extractor_examples": entity_extractor_role.get_examples_as_str(),
            "triple_extractor_examples": triple_extractor_role.get_examples_as_str(),
        }

        logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Calling Agents ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        result: CrewOutput = crew.kickoff(inputs=graph_creation_inputs)

        logger.info(".................................................................................")
        logger.info(type(result))
        logger.info(pprint(json.loads(result.json)))
        logger.info(".................................................................................")
        
        result_dict = json.loads(result.json)
        chunk["named_entities"] = result_dict["named_entities"]
        chunk["triples"] = result_dict["triples"]
    
    return document_chunks


document_chunks = extend_document_chunks_with_entities_and_triples(document_chunks)

save_document_structure(document_chunks, f"{document_name.rsplit(".", 1)[0]}_document_structure.pkl")
