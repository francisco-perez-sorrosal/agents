import os
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import BaseDocumentTransformer, Document
import uuid
import pickle

from crewai_tools import tool
from llm_foundation import logger


def load_pdf(file_path:str = "2405.14831v1.pdf"): 

    doc_loader = PyPDFLoader(file_path)
    pages = doc_loader.load_and_split()
    return "\n".join([p.page_content for p in pages])


def split_text(text: str, chunk_size: int=1000, char_overlap: int=0) -> List[Document]:

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=char_overlap,
        length_function=len,
        is_separator_regex=False,
    )

    return text_splitter.create_documents([text])


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


@tool
def filter_named_entities(document_structure_with_entities_and_triples: List[dict]) -> List[dict]:
    """Filters named entities from a list of document chunks.

    Args:
        document_structure_with_entities_and_triples (List[dict]): A list of dictionaries containing 
        the document structure with entities and triples.

    Returns:
        List[dict]: A list of the document chunks with the extracted named entities mentioned in the document.
    """
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
    return document_structure_with_entities_and_triples[:1] # TODO Remove this filter!!!! Just for testing
