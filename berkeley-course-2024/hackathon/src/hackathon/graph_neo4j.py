###################################################################################################
# Neo4J graph functions
###################################################################################################

import uuid

import numpy as np

from typing import Dict, List
from pydantic import BaseModel
from hackathon.utils import Neo4jClientFactory

from llm_foundation import logger


def clean_db(neo4j_factory: Neo4jClientFactory):
    kg = neo4j_factory.langchain_client()
    logger.info("Cleaning Neo4j database")
    
    query = """
    MATCH (n)
    DETACH DELETE n
    """
    result = kg.query(query)
    logger.info(f"Result after deleting nodes:\n{result}")


    query = """
    MATCH (n)
    CALL apoc.meta.nodeTypeProperties(n) YIELD propertyName
    REMOVE n[propertyName]
    """
    result = kg.query(query)
    logger.info(f"Result after properties:\n{result}")


def add_entities(neo4j_factory: Neo4jClientFactory, entities_embeddings, named_entities_dict: Dict):
    kg = neo4j_factory.langchain_client()
    
    entities = list(named_entities_dict.keys())
    all_entities = [{"name": entity, "node_id": named_entities_dict[entity], "embedding": entities_embeddings[named_entities_dict[entity]]} for entity in entities]

    query = """
    UNWIND $all_entities AS ae
    MERGE (a:Entity {name: ae.name, node_id: ae.node_id, embedding: ae.embedding})
    """
    kg.query(query, {"all_entities": all_entities})

def add_relates_to_relationships(neo4j_factory: Neo4jClientFactory, doc_structure):
    kg = neo4j_factory.langchain_client()
    
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

def build_vector_index(neo4j_factory: Neo4jClientFactory, idx_name = "entityIdx", emb_dim=256, sim_func='cosine'):
    kg = neo4j_factory.langchain_client()
    
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

def add_similar_entities(neo4j_factory: Neo4jClientFactory, similar_entities: List):
    kg = neo4j_factory.langchain_client()
    
    query = """
    UNWIND $similar_entities AS se
    MATCH (a:Entity {name: se.entity}), (b:Entity {name: se.similar_entity})
    MERGE (a)-[:SIMILAR_TO]->(b)
    """
    kg.query(query, {"similar_entities": similar_entities})

#### User Database ####

class User(BaseModel):
    name: str
    last_name: str
    
    def __str__(self):
        return f"{self.name} {self.last_name}"


def add_users(neo4j_factory: Neo4jClientFactory, embeddings: np.ndarray, users: List[User]):
    kg = neo4j_factory.langchain_client()
    
    all_users = []
    for user, emb in zip(users, embeddings):
        uuid_text = f"{user.name} {user.last_name}"
        generated_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, uuid_text))
        all_users.append({"uid": generated_uuid, "type": "user", "name": user.name, "last_name": user.last_name, "embedding": emb})

    print(f"Number of users to add: {len(all_users)}")

    query = """
    UNWIND $all_users AS au
    MERGE (a:Entity {node_id: au.uid, type: au.type, name: au.name, last_name: au.last_name, embedding: au.embedding})
    """
    kg.query(query, {"all_users": all_users})
