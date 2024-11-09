# Express
from shiny import reactive
from shiny.express import input, render, ui 
from datetime import datetime
from .chat_page import chat_page
from .graph_page import graph_page


# Configure Shiny page
ui.page_opts(
    title="Neurogen",
    fillable=True,
    fillable_mobile=True,
)

ui.nav_spacer()

with ui.sidebar():
    ui.h1("Neurogen")
    ui.input_text("text_in", "Type something here:")


with ui.nav_panel("Chat Page"):
    chat_page("chat_page")

with ui.nav_panel("Graph Page"):
    graph_page("graph_page", sidebar_text=input.text_in)

# with ui.card():
#     ui.h2("Graph Page")