###################################################################################################
# Neo4J graph functions
###################################################################################################

import numpy as np
import igraph as ig

from typing import Dict, List
from langchain_community.graphs import Neo4jGraph
from neo4j import GraphDatabase

from llm_foundation import logger


def clean_db(kg: Neo4jGraph):
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


def add_entities(kg: Neo4jGraph, entities_embeddings, named_entities_dict: Dict):

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


def pagerank(uri: str, auth: str, nodes, entities_ref_count_matrix):
    
    # remove duplicated nodes
    unique_data = {}
    for item in nodes:
        unique_data[item['id']] = item

    unique_nodes = list(unique_data.values())

    with GraphDatabase.driver(uri, auth=auth) as driver:
        with driver.session() as session:
            
            # Get entities and relations and create the graph
            entities = session.execute_read(lambda tx: tx.run("MATCH (n:Entity) RETURN n.node_id AS node_id").data())
            relations = session.execute_read(lambda tx: tx.run("MATCH (a)-[r:RELATES_TO]->(b) RETURN a.node_id AS source, b.node_id AS target").data())

            # Create an igraph graph
            g = ig.Graph(directed=True) 
            
            # Build graph
            for gnode in entities:    
                g.add_vertex(name=str(gnode["node_id"]), labels=str(gnode["node_id"]))

            # add edges
            g.add_edges([(str(rel["source"]), str(rel["target"])) for rel in relations])

            # Personalized PageRank
            personalization = [0] * len(g.vs)
            # Set personalization vector 
            personalization_value  = 1.0 / len(nodes)
            for node in unique_nodes:
                idx = g.vs.find(name=str(node["id"])).index
                personalization[idx] += personalization_value 

                # calculate node specificity len(node_passages) ** -1
                node_sum = np.sum(entities_ref_count_matrix[node["id"]])
                if node_sum == 0:
                    logger.warning(f"Node sum for node {node['id']} is zero", node)
                else:
                    personalization[idx] *= node_sum ** -1
                    logger.info(f"Node sum{node['id']}: {node_sum} personalization: {personalization[idx]}")

            #https://igraph.org/python/api/0.9.11/igraph._igraph.GraphBase.html#personalized_pagerank
            pagerank_scores = g.personalized_pagerank(damping=0.85, reset=personalization)

    return pagerank_scores
