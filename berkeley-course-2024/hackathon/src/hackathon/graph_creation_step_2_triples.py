import json
import pprint
import pickle
import hashlib

from typing import Dict, List
import numpy as np

from crewai import Agent, Task, Crew
from crewai.crews import CrewOutput
from llm_foundation import logger
from llm_foundation.agent_types import Persona, Role
from pydantic import BaseModel
from rich import print
from rich.pretty import pprint

from hackathon.tools import load_pdf, split_text

document_name: str = "2405.14831v1.pdf"
document_structure_file = f"{document_name.rsplit(".", 1)[0]}_document_structure.pkl"


logger.info(f"Loading document structure from {document_structure_file}")
document_structure_with_entities_and_triples = pickle.load(open(document_structure_file, "rb"))

assert len(document_structure_with_entities_and_triples) == 1  ## TODO Remove this filter!!!! Just for testing

# logger.info(document_structure_with_entities_and_triples)

def filter_named_entities(document_structure_with_entities_and_triples: List[dict]) -> List[dict]:
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


document_structure_with_entities_and_triples = filter_named_entities(document_structure_with_entities_and_triples)

def create_document_deduped_entities_dict(document_structure_with_entities_and_triples: List[dict]) -> Dict[str, str]:
    
    named_entities_dict = {}
    next_idx_for_named_entity = 0
    
    for chunk_info in document_structure_with_entities_and_triples:
        
        # def hash_string(s: str) -> str:
        #     hash_object = hashlib.sha256(s.encode())
        #     hex_digest = hash_object.hexdigest()
        #     return hex_digest
        
        named_entities = chunk_info["named_entities"]
        for i, named_entity in enumerate(named_entities):
            if named_entity not in named_entities_dict:
                # entity_hashed = hash_string(named_entity)
                # logger.info(f"{i} Adding named entity: {named_entity} with hash: {entity_hashed}")
                # Do not use hash as we need the overall matrix of the document for the pagerank computation
                # named_entities_dict[named_entity] = entity_hashed
                named_entities_dict[named_entity] = next_idx_for_named_entity
                next_idx_for_named_entity += 1

    return named_entities_dict

entity2uid_dict = create_document_deduped_entities_dict(document_structure_with_entities_and_triples)

logger.info(pprint(entity2uid_dict))

def create_matrix_entity_ref_count(document_structure_with_entities_and_triples: List[dict], named_entities_dict: dict) -> np.ndarray:
    n_of_entities = len(named_entities_dict)
    n_of_chunks = len(document_structure_with_entities_and_triples)
    
    document_chunks = document_structure_with_entities_and_triples
    entity_per_chunk_count_matrix = np.zeros((n_of_entities, n_of_chunks))
    for chunk_idx, chunk_info in enumerate(document_chunks):
        named_entities = chunk_info["named_entities"]
        for named_entity in named_entities:
            named_entity_hash = named_entities_dict[named_entity.lower()]
            # Count of named_entity appearing in the document chunk
            entity_per_chunk_count_matrix[named_entity_hash][chunk_idx] = chunk_info["text"].lower().count(named_entity.lower())
    return entity_per_chunk_count_matrix


matrix = create_matrix_entity_ref_count(document_structure_with_entities_and_triples, entity2uid_dict)

example_chunk = document_structure_with_entities_and_triples[0]



n_of_entities = len(entity2uid_dict)
n_of_chunks = len(document_structure_with_entities_and_triples)

for e_idx in range(n_of_entities):
    entity_name = list(entity2uid_dict.keys())[list(entity2uid_dict.values()).index(e_idx)]
    logger.info(f"Entity: {e_idx} {entity_name} Per chunk count: {matrix[e_idx][:]}")

# Save the matrix to a file
with open(f"{document_name.rsplit(".", 1)[0]}_entity2uid_dict.pkl", "wb") as f:
    pickle.dump(entity2uid_dict, f)
logger.info(f"entity2uid_dict has been saved to {document_name.rsplit(".", 1)[0]}_entity2uid_dict.pkl")
