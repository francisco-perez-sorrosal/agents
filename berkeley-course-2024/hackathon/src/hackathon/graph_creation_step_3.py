import os
import pickle

from typing import Dict, List, Optional

import faiss
import numpy as np

from langchain_openai import OpenAIEmbeddings
from langchain_community.graphs import Neo4jGraph

from llm_foundation import logger


NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
NEO4J_DATABASE = os.environ["NEO4J_DB"] 

document_name: str = "2405.14831v1.pdf"

# Embeddings and FAISS index params
emb_dimension = 256
M = 32
recall_at_k = 3  # how far in the indices/distances we go

# M_max defines the maximum number of links a vertex can have, and M_max0, which defines the same but for vertices in layer 0.
M = 64  # for HNSW index, the number of neighbors we add to each vertex on insertion. 
# Faiss sets M_max and M_max0 automatically in the set_default_probas method, at index initialization. 
# The M_max value is set to M, and M_max0 set to M*2

###################################################################################################
# Index and Embeddings functions
###################################################################################################

def generate_entity_embeddings(entities: list, emb_dimension: int = 256, emb_save_path: Optional[str] = None):
    openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=emb_dimension)
    entities_embeddings = openai_embeddings.embed_documents(entities)  # Embeddings are a list of list of floats
    logger.debug(f"Entities embeddings: {entities_embeddings}")
    
    if emb_save_path:
        with open(emb_save_path, "wb") as f:
            pickle.dump(entities_embeddings, f)
    
    return entities_embeddings


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

###################################################################################################
# Index and Embeddings Creation
###################################################################################################

logger.info(f"Generating embeddings for named entities in document: {document_name}")
named_entities_dict = pickle.loads(open(f"{document_name.rsplit(".", 1)[0]}_entity2uid_dict.pkl", "rb").read())
logger.info(f"Named entities dict loaded: {named_entities_dict}")
entities = list(named_entities_dict.keys())
logger.info(f"Number of entities: {len(entities)}. First entity is: {entities[0]}")

logger.info("Generate entity embeddings")
embeddings_filepath = f"{document_name.rsplit('.', 1)[0]}_entity_embeddings.pkl"
entities_embeddings = generate_entity_embeddings(entities, emb_dimension, embeddings_filepath)

entities_embeddings = pickle.loads(open(embeddings_filepath, "rb").read())
embs_as_nparrays = np.array(entities_embeddings)

faiss_index = create_index(embs_as_nparrays, emb_dimension, M)
# We query with the same elements we indexed
distances, indexes = search_index(faiss_index, embs_as_nparrays, recall_at_k)
similar_entities = build_similar_entities(entities, indexes, distances, recall_at_k, max_distance=0.85)  # Original max_distance=0.7
logger.info(f"Similar entities:\n{similar_entities}")

# TODO Scores discarded for now
# scores = calculate_scores(distances)
# similar_entities_score = build_similar_entities_with_scores(entities, indexes, scores, recall_at_k, min_score=0.5)            
# logger.info(similar_entities_score)


###################################################################################################
# Neo4J graph functions
###################################################################################################

def add_entities(kg: Neo4jGraph, named_entities_dict: Dict):

    entities = list(named_entities_dict.keys())

    all_entities = [{"name": entity, "node_id": named_entities_dict[entity], "embedding": entities_embeddings[named_entities_dict[entity]]} for entity in entities]

    query = """
    UNWIND $all_entities AS ae
    MERGE (a:Entity {name: ae.name, node_id: ae.node_id, embedding: ae.embedding})
    """
    kg.query(query, {"all_entities": all_entities})

def add_relates_to_relationships(kg: Neo4jGraph, doc_structure):
    triplets = []
    for chunk in doc_structure:
        for triple in chunk["triples"]:
            if len(triple) != 3:
                continue
            subject=triple[0].lower()
            predicate=triple[1].replace(" ", "_").upper()
            object=triple[2].lower()
            triplets.append({
                "subject": subject, 
                "predicate": predicate, 
                "object": object,
                "passageId_subject": chunk["id"],
                "passageId_object": chunk["id"],
            })
    
    query = """
    UNWIND $triplets AS triplet
    MATCH (a:Entity {name: triplet.subject}), (b:Entity {name: triplet.object})
    MERGE (a)-[:RELATES_TO {type: triplet.predicate}]->(b)
    """
    kg.query(query, {"triplets": triplets})

def build_vector_index(kg: Neo4jGraph, idx_name = "entityIdx", emb_dim=256, sim_func='cosine'):
    query = """
    CREATE VECTOR INDEX $idx_name IF NOT EXISTS
    FOR (m:Entity)
    ON m.embedding
    OPTIONS {indexConfig: {
        `vector.dimensions`: $emb_dim,
        `vector.similarity_function`: $sim_func
    }}
    """
    kg.query(query, {'idx_name': idx_name, 'emb_dim': emb_dim, 'sim_func': sim_func})

def add_similar_entities(kg: Neo4jGraph, similar_entities: List):
    query = """
    UNWIND $similar_entities AS se
    MATCH (a:Entity {name: se.entity}), (b:Entity {name: se.similar_entity})
    MERGE (a)-[:SIMILAR_TO]->(b)
    """
    kg.query(query, {"similar_entities": similar_entities})

###################################################################################################
# Create the Neo4J graph!!!
###################################################################################################

kg = Neo4jGraph(
    url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, database=NEO4J_DATABASE
)

# Step 1: Add all entities to the graph
add_entities(kg, named_entities_dict)

# Step 2: Add RELATES_TO relationships
doc_structure = pickle.loads(open(f"{document_name.rsplit(".", 1)[0]}_document_structure.pkl", "rb").read())
add_relates_to_relationships(kg, doc_structure)

# Step 3: Add SIMILAR_TO relationships
add_similar_entities(kg, similar_entities)

# Step 4: Build vector index
build_vector_index(kg)
