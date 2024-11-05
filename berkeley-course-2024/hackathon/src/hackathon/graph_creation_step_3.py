import os
import pickle

from typing import Dict, List, Optional

import numpy as np

from langchain_community.graphs import Neo4jGraph
from hackathon.index import generate_entity_embeddings, create_index, search_index, calculate_scores, build_similar_entities
from hackathon.graph_neo4j import add_entities, add_relates_to_relationships, build_vector_index, add_similar_entities
from llm_foundation import logger


NEO4J_URI = os.environ["NEO4J_URI"]
NEO4J_USERNAME = os.environ["NEO4J_USERNAME"]
NEO4J_PASSWORD = os.environ["NEO4J_PASSWORD"]
NEO4J_DATABASE = os.environ["NEO4J_DB"] 

document_name: str = "2405.14831v1.pdf"

# Embeddings and FAISS index params
emb_dimension = 256
recall_at_k = 3  # how far in the indices/distances we go

# M_max defines the maximum number of links a vertex can have, and M_max0, which defines the same but for vertices in layer 0.
M = 64  # for HNSW index, the number of neighbors we add to each vertex on insertion. 
# Faiss sets M_max and M_max0 automatically in the set_default_probas method, at index initialization. 
# The M_max value is set to M, and M_max0 set to M*2

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
# Create the Neo4J graph!!!
###################################################################################################

kg = Neo4jGraph(
    url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD, database=NEO4J_DATABASE
)

# Step 1: Add all entities to the graph
add_entities(kg, entities_embeddings, named_entities_dict)

# Step 2: Add RELATES_TO relationships
doc_structure = pickle.loads(open(f"{document_name.rsplit(".", 1)[0]}_document_structure.pkl", "rb").read())
add_relates_to_relationships(kg, doc_structure)

# Step 3: Add SIMILAR_TO relationships
add_similar_entities(kg, similar_entities)

# Step 4: Build vector index
build_vector_index(kg)
