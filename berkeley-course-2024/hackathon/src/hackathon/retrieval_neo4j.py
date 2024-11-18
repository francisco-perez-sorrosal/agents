import numpy as np
import igraph as ig

from typing import Any, List, Tuple

from langchain_openai import OpenAIEmbeddings
from llm_foundation import logger
from hackathon.utils import Neo4jClientFactory


def pagerank(neo4j_conn: Neo4jClientFactory, nodes: List[Any], entities_ref_count_matrix):
    
    # Remove duplicated nodes
    unique_data = {}
    for item in nodes:
        unique_data[item['id']] = item

    unique_nodes = list(unique_data.values())

    with neo4j_conn.neo4j_client() as driver:
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


def search_similar_entities(neo4j_conn: Neo4jClientFactory, query_entity: str,
                            emb_model: str = "text-embedding-3-small",
                            emb_dim: int = 256,
                            min_score: float=0.8):
    
    # Embed the query entity
    openai_embeddings = OpenAIEmbeddings(model=emb_model, dimensions=emb_dim)
    query_entity_embedding = openai_embeddings.embed_query(query_entity)
    
    results = []
    with neo4j_conn.neo4j_client() as driver:
        with driver.session() as session:
            
            def search_vector(tx, query_embedding):
                cypher_query = f"""
                CALL db.index.vector.queryNodes('entityIdx', 3, {query_embedding}) YIELD node, score
                RETURN node.node_id as id, node.name as name, coalesce(node.last_name, null) AS last_name, score
                """
                return tx.run(cypher_query).data()
            # Search for the root nodes of entities similar to the query entity using the embeddings
            graph_results = session.execute_read(lambda tx: search_vector(tx, query_entity_embedding))
            
            # Filter the results by the minimum score
            for result in graph_results:
                if result["score"] >= min_score:
                    results.append(result)

            def similar_search(tx, similar_entities):
                
                cypher_query = f"""
                MATCH (a:Entity)-[:SIMILAR_TO]->(b:Entity)
                WHERE a.name IN $similar_entities
                RETURN b.node_id AS id, b.name AS name
                """
                return tx.run(cypher_query, similar_entities=similar_entities).data()

            # Expand the similar results navigating the entity nodes retrieved above, 
            # using the SIMILAR_TO entities
            similar_entities = [ result["name"] for result in results]
            graph_results = session.execute_read(lambda tx: similar_search(tx, similar_entities))
            results.extend(graph_results)

    return results


def retrieve_similar_entities(neo4j_conn: Neo4jClientFactory, entities, emb_dim: int = 256):        
    '''For every entity in the list of entitities, find the nodes in the graph DB 
    similar to those named entities'''
    similar_nodes = []
    if len(entities) == 0:
        logger.info("No named entities found in the query")
    else:
        for entity in entities:
            results = search_similar_entities(neo4j_conn, entity, emb_dim=emb_dim)
            similar_nodes.extend(results)
    return similar_nodes


def chunk_ranker(entity2chunkrefs_count_matrix, pg_rank_scores) -> Tuple:
    chunk_scores = np.dot(entity2chunkrefs_count_matrix.T, np.array(pg_rank_scores))
    logger.warning(f"Chunk Scores:\n{chunk_scores}")
    logger.warning(f"Chunk Indexes:\n{np.argsort(chunk_scores)[::-1]}")
    return chunk_scores, np.argsort(chunk_scores)[::-1]


def retrieve_context(doc_structure: List[Any], chunks_score, best_chunk_idxs_ordered, max_chunks:int = 3):
    '''Build the best context for the query based on the retrieved chunks'''
    
    context = ""
    chunks_count = 0
    for idx in best_chunk_idxs_ordered:
        if chunks_score[idx] > 0:
            if chunks_count > max_chunks-1:
                break
            chunks_count += 1
            context += f"{doc_structure[idx]['text']}\n\n"

    return context
