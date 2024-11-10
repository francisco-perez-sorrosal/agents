
from shiny.express import input, render, ui, module

from shiny import reactive
from hackathon.retrieval_agent import answer_query, extract_named_entities

from llm_foundation import logger

# from rich import print_json

@module
def chat_page(input, output, session):
    ui.h2("Chat Page")
    
    query_extracted_named_entities = reactive.value([])
    
    ui.input_selectize(
        "test_question", "Select a test question",
        ["What is the meaning of Francisco's life?", 
        "What is the capital of France?", 
        "What is the square root of 16?"],
        selected=None,
    )    
    
    @render.text
    def display_named_entities():
        return f"Query extracted named entities:\n{query_extracted_named_entities.get()}"
    
    
    # Create a chat
    chat = ui.Chat(
        id="chat",
        messages=["welcome"],
    )
    
    @reactive.effect
    @reactive.event(input.test_question)
    def update_test_question_in_chat_user_input():
        logger.info(f"Test question selected: {input.test_question()}")
        chat.update_user_input(value=input.test_question())

    # Display it
    chat.ui(placeholder="Type your question here... or select a test question above")

    @chat.on_user_submit
    async def _():
        # Get the user's input
        
        user_input = chat.user_input()
        if not user_input:
            logger.warning("User input is empty!!!!")
            return

        # Extract entities from the user's input query        
        logger.info(".................................................................................")
        extracted_named_entities = extract_named_entities(user_input)
        logger.info(f"Query entities: {extracted_named_entities}")
        logger.info(".................................................................................")
        query_extracted_named_entities.set(extracted_named_entities)
        
        # TODO # Implement context retrieval

        retrieved_context = "The meaninig of life is 42"
        result = answer_query(user_input, context=retrieved_context)
        # Append a response to the chat
        await chat.append_message(f"Savant said: {result.raw}")
