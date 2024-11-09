
from shiny.express import input, render, ui, module


@module
def chat_page(input, output, session):
    ui.h2("Chat Page")
    
    # Create a chat
    chat = ui.Chat(
        id="chat",
        messages=["welcome"],
    )

    # Display it
    chat.ui()

    @chat.on_user_submit
    async def _():
        # Get the user's input
        user = chat.user_input()
        # Append a response to the chat
        await chat.append_message(f"You said: {user}")