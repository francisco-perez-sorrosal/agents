from shiny.express import ui, module, render
from shiny import reactive

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
