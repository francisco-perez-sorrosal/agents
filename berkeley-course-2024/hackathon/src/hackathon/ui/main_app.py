import os
from shiny.express import input, ui, app_opts
from .chat_page import chat_page
from .graph_page import graph_page
from langtrace_python_sdk import langtrace  # Must precede any llm module imports

from llm_foundation import logger


# WWW directory definition for static assets
DIR = os.path.dirname(os.path.abspath(__file__))
WWW = os.path.join(DIR, "www")


# We need to load the .env file in a function, otherwise there's an weird Shiny-related error
def load_dotenv():
    import dotenv
    dotenv.load_dotenv()

load_dotenv()
logger.info(f"Observing agents: {bool(os.environ.get("OBSERVE_AGENTS"))}")
if bool(os.environ.get("OBSERVE_AGENTS")):
    langtrace.init()

logger.info("Starting main app...")

# Configure Shiny page
app_opts(static_assets=WWW)
ui.page_opts(
    title="Neurogen",
    fillable=True,
    fillable_mobile=True,
)

ui.nav_spacer()

with ui.sidebar():
    ui.h1("Neurogen")
    ui.input_text("text_in", "Type something here (Useless now):")


with ui.nav_panel("Chat Page"):
    chat_page("chat_page")

with ui.nav_panel("Graph Page"):
    graph_page("graph_page", sidebar_text=input.text_in)
