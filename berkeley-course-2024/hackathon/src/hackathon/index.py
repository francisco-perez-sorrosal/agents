###################################################################################################
# Index and Embeddings functions
###################################################################################################

import pickle

import faiss
import numpy as np

from numpy.typing import NDArray
from typing import Any, Optional
from langchain_openai import OpenAIEmbeddings
from llm_foundation import logger


def generate_entity_embeddings(entities: list, emb_dimension: int = 256, emb_save_path: Optional[str] = None) -> NDArray[Any]:
    openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=emb_dimension)
    entities_embeddings = openai_embeddings.embed_documents(entities)  # Embeddings are a list of list of floats
    logger.debug(f"Entities embeddings: {entities_embeddings}")
    
    if emb_save_path:
        with open(emb_save_path, "wb") as f:
            pickle.dump(entities_embeddings, f)
    
    return np.array(entities_embeddings)


def create_index(vectors: np.ndarray, emb_dimension: int, M: int) -> faiss.IndexHNSWFlat:
    # See https://www.pinecone.io/learn/series/faiss/hnsw/ for info about HNSW
    # See also https://bakingai.com/blog/hnsw-semantic-search-faiss-integration/
    faiss_index = faiss.IndexHNSWFlat(emb_dimension, M)

    # convert to numpy array

    faiss_index.add(vectors)  # Build the index

    return faiss_index

def search_index(faiss_index: faiss.IndexHNSWFlat, query: list, recall_at_k: int) -> tuple:
    distances, indices = faiss_index.search(query, recall_at_k)
    logger.info(f"\nDistances:\n{np.round(distances, 3)}\nIndices:\n{indices}")
    
    return distances, indices

def calculate_scores(distances: list) -> list:
    scores = 1 / (1 + distances)  # Inverting distances to get similarity scores.
    print("Similarity Scores: ", scores)
    return scores

def build_similar_entities(entities: list, indices: list, distances: list, recall_at_k: int, max_distance: float=0.7) -> list:
    similar_entities = []
    for idx, entity in enumerate(entities):
        for i in range(recall_at_k):
            if indices[idx][i] != idx and distances[idx][i] <= max_distance:
                logger.info(f"Similarity (<={max_distance} dist) found for {entity} ({idx}) with {entities[indices[idx][i]]} ({indices[idx][i]}): Distance {distances[idx][i]}")
                similar_entities.append(
                    {
                        "entity": entity, 
                        "similar_entity": entities[indices[idx][i]]
                    }
                )
    return similar_entities

# TODO Not used for now
# https://medium.com/@asakisakamoto02/how-to-use-faiss-similarity-search-with-score-explained-99ea3fe964cf
def build_similar_entities_with_scores(entities: list, indices: list, scores: list, recall_at_k: int, min_score: float=0.5) -> list:
    similar_entities = []
    for idx, entity in enumerate(entities):
        for i in range(recall_at_k):
            if indices[idx][i] != idx and scores[idx][i] > min_score:
                logger.info(f"Similarity (>{min_score} score) found for {entity} ({idx}) with {entities[indices[idx][i]]} ({indices[idx][i]}): Score {scores[idx][i]}")
                similar_entities.append(
                    {
                        "entity": entity, 
                        "similar_entity": entities[indices[idx][i]]
                    }
                )
    return similar_entities
