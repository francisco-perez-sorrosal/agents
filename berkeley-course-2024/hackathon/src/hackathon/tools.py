import os
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import BaseDocumentTransformer, Document
import uuid
import pickle

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
    
