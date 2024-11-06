from graphiti_core.edges import EntityEdge

def edges_to_facts_string(entities: list[EntityEdge]):
    """Funcion that converts the edge results into a readable string format"""
    return '\n'.join([f"- {edge.fact}" for edge in entities])