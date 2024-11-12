import os

import neo4j

from pyvis.network import Network
from shiny.express import ui, module, render
from shiny import reactive

from llm_foundation import logger
from hackathon.graph_neo4j import Neo4jClientFactory

# WWW directory definition for static assets
DIR = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(DIR, "www")
NEO4J_GRAPH_PYVIS_OUTPUT_ID = "neo4j_graph"

@module
def graph_page(input, output, session, sidebar_text):
    text = reactive.value("N/A")

    ui.h2("Graph Page")
    
    @reactive.effect
    @reactive.event(sidebar_text)
    def get_sidebar_text_events():
        text.set(str(sidebar_text.get()))
    
    @render.code
    def out():
        return f"Sidebar text says {str(text.get())}"
    
    with ui.card(full_screen=True):
        
        @render.ui()
        def graph():
            neo4j_factory = Neo4jClientFactory()
            graph_driver = neo4j_factory.neo4j_client()
            
            query_graph = graph_driver.execute_query("MATCH (n) OPTIONAL MATCH (n)-[r]->() RETURN n, r LIMIT 100",
                                                name="Neurogen Graph",
                                                result_transformer_=neo4j.Result.graph,)
            visual_graph = Network()
            
            nodes_text_properties = {  # property shown as text per node
                "Entity": "name",
                "Episodic": "name",
            }
            
            for node in query_graph.nodes:
                node_label = list(node.labels)[0]
                node_text = node[nodes_text_properties[node_label]]
                visual_graph.add_node(node.element_id, node_text, group=node_label)
            
            for relationship in query_graph.relationships:
                logger.info(f"Relationship: {relationship}")
                visual_graph.add_edge(
                    relationship.start_node.element_id,
                    relationship.end_node.element_id,
                    title=relationship.type
                )
            
            # Visualize the graph as an iframe: https://github.com/posit-dev/py-shinywidgets/issues/63
            visual_graph.generate_html(local=False)
            file = os.path.join(WWW, NEO4J_GRAPH_PYVIS_OUTPUT_ID + ".html")
            with open(file, "w") as f:
                f.write(visual_graph.html)
                
            return ui.tags.iframe(
                src=f"{NEO4J_GRAPH_PYVIS_OUTPUT_ID}.html",
                style="height:600px;width:100%;",
                scrolling="yes",
                seamless="seamless",
                frameBorder="3",
            )
