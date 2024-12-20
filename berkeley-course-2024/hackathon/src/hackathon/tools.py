import hashlib
import logging
import os
import pickle
import re
import uuid
from typing import Dict, List, Optional, Callable, Any

import numpy as np
import requests
from crewai.tools import BaseTool
from crewai_tools import tool
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from llm_foundation import logger
from pydantic import BaseModel, Field, PrivateAttr
from requests import RequestException

from hackathon.retrieval_neo4j import retrieve_similar_entities
from hackathon.utils import Neo4jClientFactory


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
        # Augment with entities identified in the triples
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

###################################################################################################
# File download tool
###################################################################################################

class FileDownloadToolInput(BaseModel):
    url: str = Field(..., description="URL of the file to download")
    filename: str = Field(..., description="Name to save the file as")
    directory: Optional[str] = Field("./", description="Directory to save the file in")

# Define the type alias for the filename generator function
FilenameGenerator = Callable[[str, bytes], str]


def identity_filename_generator(original_filename: str, content: bytes) -> str:
    return original_filename


# Define the SHA-256 filename generator function
def sha256_filename_generator(original_filename: str, content: bytes, ) -> str:
    file_hash = hashlib.sha256(content).hexdigest()
    return f"{file_hash}_{original_filename}"


# Define the UUID4 filename generator function
def uuid4_filename_generator(original_filename: str, content: bytes) -> str:
    return f"{uuid.uuid4()}_{original_filename}"


class FileDownloadTool(BaseTool):
    """
    A tool to download a file from a given URL and save it locally
    """
    name: str = "File Downloader"
    description: str = "Downloads a file from a given URL and saves it locally"
    args_schema: type[BaseModel] = FileDownloadToolInput
    _filename_generator: FilenameGenerator = PrivateAttr()

    def __init__(self, *, filename_generator: FilenameGenerator = identity_filename_generator, **data: Any):
        super().__init__(**data)
        self._filename_generator = filename_generator

    def run(self, url: str, filename: str, directory: str = "./") -> str:
        return self._run(url, filename, directory)

    def _run(self, url: str, filename: str, directory: str = "./") -> str:
        logging.debug(f"Running download tool with URL: {url}, filename: {filename}, directory: {directory}")
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

            # Create the directory if it doesn't exist
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # Generate the unique filename using the instance's _filename_generator function
            unique_filename = self._filename_generator(filename, response.content)
            logging.debug(f"Generated unique filename: {unique_filename}")

            # Construct the full path
            filepath = os.path.join(directory, unique_filename)

            # Write the file
            with open(filepath, 'wb') as f:
                f.write(response.content)

            logging.debug(f"File downloaded successfully. Filepath: {filepath}, Source url: {url}")
            return f'File downloaded successfully. Filepath: {filepath}, Source url: {url}'

        except RequestException as e:
            return f'Error downloading file: {str(e)}'
        except OSError as e:
            return f'Error saving file: {str(e)}'
        except Exception as e:
            return f'Error downloading file, unexpected error: {str(e)}'


###################################################################################################
# GraphDB tools
###################################################################################################

def graphdb_retrieval(doc: str) -> List:
    neo4j_factory = Neo4jClientFactory()
    return retrieve_similar_entities(neo4j_factory, [doc], emb_dim=256)  #Fix here the emb_dim


@tool
def graphdb_retrieval_tool(doc: str) -> List:
    """Retrieve documents (e.g. entities, users, etc..) from a graph database.
    """
    return graphdb_retrieval(doc)
