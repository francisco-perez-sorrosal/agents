import os
from typing import Dict, List, Optional

import numpy as np
import pickle
import re
import uuid

from crewai_tools import tool
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers.json import SimpleJsonOutputParser

from llm_foundation import logger


def get_uuid(string: str):
    return uuid.UUID(string)


def save_doc(doc_name: str, chunks: List[Document], with_uuid_name: bool = True):

    chunks_arr = [ { "id": idx, "text": chunk.page_content } for idx, chunk in enumerate(chunks)]

    for chunk in chunks_arr:
        chunk["named_entities"] =[]
        chunk["triples"] = []
        try:
            # json_output_parser = SimpleJsonOutputParser()
            # chain_entities = extract_entities_prompt | ChatOpenAI(model=llm_model, temperature=0.0) | json_output_parser
            # named_entities = chain_entities.invoke({"passage_text": chunk["text"]})
            chunk["named_entities"] = named_entities["entities"]

            # chain_triples = extract_triplets_prompt | ChatOpenAI(model=llm_model, temperature=0.0) | json_output_parser
            # triples = chain_triples.invoke({"passage_text": chunk["text"], "entities": named_entities})
            # chunk["triples"] = triples["triples"]
        except Exception as e:
            print(f"Error processing passage: {e}")
            continue
    
    # Save the chunks to disk
    if with_uuid_name:
        doc_name = f"{str(get_uuid(doc_name))}.pkl"
    else:
        file_name, _ = os.path.splitext(doc_name)
        doc_name = f"{file_name}.pkl"
    pickle.dump(chunks_arr, open(doc_name, "wb"))
    print(f"{doc_name} saved!")
    

###################################################################################################
# Crew AI tools
###################################################################################################


@tool
def read_file(filename:str):
    """Reads a file from disk.
    It returns the content of the file.
    """
    logger.info(f"Loading document structure from {filename}")
    return pickle.load(open(filename, "rb"))


def filter_named_entities(document_structure_with_entities_and_triples: List[dict]) -> List[dict]:
    for chunk_info in document_structure_with_entities_and_triples:        
        named_entities = [entity.lower() for entity in chunk_info["named_entities"]]
        logger.debug(named_entities)
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
    return document_structure_with_entities_and_triples


@tool
def filter_named_entities_tool(document_structure_with_entities_and_triples: List[dict]) -> List[dict]:
    """Filters named entities from a list of document chunks.

    Args:
        document_structure_with_entities_and_triples (List[dict]): A list of dictionaries containing 
        the document structure with entities and triples.

    Returns:
        List[dict]: A list of the document chunks with the extracted named entities mentioned in the document.
    """
    return filter_named_entities(document_structure_with_entities_and_triples)


def create_document_deduped_entities_dict(document_structure_with_entities_and_triples: List[dict]) -> Dict[str, str]:
    named_entities_dict = {}
    next_idx_for_named_entity = 0
    
    for chunk_info in document_structure_with_entities_and_triples:
        assert chunk_info.get("named_entities", None) is not None, "Document chunk should contain named_entities!"
        named_entities = chunk_info["named_entities"]
        for named_entity in named_entities:
            if named_entity not in named_entities_dict:
                named_entities_dict[named_entity] = next_idx_for_named_entity
                next_idx_for_named_entity += 1

    return named_entities_dict


@tool
def create_document_deduped_entities_dict_tool(document_structure_with_entities_and_triples: List[dict]) -> Dict[str, str]:
    """Extract a map of entity to entity unique id (uid) from a document structure.

    Args:
        document_structure_with_entities_and_triples (List[dict]): A list of dictionaries containing 
        the document structure with entities and triples.
        
    Returns:
        Dict[str, ing]: the deduped entity to uid map
    """
    return create_document_deduped_entities_dict(document_structure_with_entities_and_triples)


def create_matrix_entity_ref_count(document_structure_with_entities_and_triples: List[dict], named_entities_dict: dict) -> np.ndarray:    
    n_of_entities = len(named_entities_dict)
    n_of_chunks = len(document_structure_with_entities_and_triples)
    
    document_chunks = document_structure_with_entities_and_triples
    entity_per_chunk_count_matrix = np.zeros((n_of_entities, n_of_chunks))
    for chunk_idx, chunk_info in enumerate(document_chunks):
        named_entities = chunk_info["named_entities"]
        for named_entity in named_entities:
            # Remove multiple spaces and new lines
            text = re.sub(' +', ' ', chunk_info["text"].lower())
            text = re.sub('\n+', ' ', text)
            named_entity_hash = named_entities_dict[named_entity.lower()]
            # Count of named_entity appearing in the document chunk
            entity_per_chunk_count_matrix[named_entity_hash][chunk_idx] = text.count(named_entity.lower())
    return entity_per_chunk_count_matrix


@tool
def create_matrix_entity_ref_count_tool(document_structure_with_entities_and_triples: List[dict], named_entities_dict: dict) -> np.ndarray:
    """Create a matrix of entity reference count per document chunk.
    
    """
    return create_matrix_entity_ref_count(document_structure_with_entities_and_triples, named_entities_dict)


def extract_entities_from_query(llm_model, user_query):
    # This prompt is a simpler version o the original, it works better for small paragraphs and less entities and
    # in other languages like portuguese
    extract_entities_custom_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """Your task is to extract all entities from the given paragraph, in the same language as the paragraph.
    Respond with a JSON list of entities like {{"entities":["entity1", "entity2", ...]}}"""),
            ("human", """Paragraph:```
    {passage_text}
    ```"""),
        ]
    )

    json_output_parser = SimpleJsonOutputParser()
    chain_query_entities = extract_entities_custom_prompt | ChatOpenAI(model=llm_model, temperature=0.0) | json_output_parser
    #chain_query_entities = extract_entities_prompt | ChatOpenAI(model=llm_model, temperature=0.0) | json_output_parser
    query_entities = chain_query_entities.invoke({"passage_text": user_query})
    query_entities["named_entities"] = query_entities["entities"] # change the name to named_entities

    return query_entities