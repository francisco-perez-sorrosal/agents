import nest_asyncio

from shiny.express import input, render, ui, module
from shiny import reactive
from hackathon.users import User, UserIdentificationFlow, UserIdentityOutput, UserIdentityValidationState
from hackathon.retrieval_agent import answer_query, extract_named_entities

from llm_foundation import logger

# from rich import print_json

# Allow nested event loop to run crewai the flows there
nest_asyncio.apply()


@module
def chat_page(input, output, session):
    ui.h2("Chat Page")
    
    user_identification_flow = reactive.value(UserIdentificationFlow())
    query_extracted_named_entities = reactive.value([])
    
    current_user_state = reactive.value(UserIdentityValidationState(user_info=[], name=None, last_name=None))
    
    ### Add hoc user scaffold
    ui.input_checkbox("adhocuser", "Add hoc user?", False)
    
    @reactive.effect
    @reactive.event(input.adhocuser)
    def adhocuser_f():
        if not input.adhocuser():
            current_user_state.set(UserIdentityValidationState(user_info=[], name=None, last_name=None))
        else:
            current_user_state.set(UserIdentityValidationState(user_info=[], name="Francisco", last_name="Perez-Sorrosal"))
            
    @render.ui
    def current_user_value():
        return f"The current user is {current_user_state.get().name} {current_user_state.get().last_name}"
    
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
        
        # Special flow to identify the user        
        current_user = current_user_state.get().get_extracted_user()
        if not current_user.is_identified(): 
            flow = user_identification_flow.get()
            current_state = current_user_state.get()
            # Add last user's message to current state context
            last_message = chat.messages(format="openai")[-1]
            current_state.user_info.append(last_message["content"])
            flow.kickoff(inputs=current_user_state.get().model_dump())
            new_state = flow.state
            if new_state.user_identified and not new_state.question:  # We identified the user so we greet them
                await chat.append_message(f"Savant said: Hello {new_state.name} {new_state.last_name}!")
            else:
                await chat.append_message(f"Savant said: {new_state.question}")
            current_user_state.set(new_state)  # Update state
        else:
            # Extract entities from the user's input query and put them into context
            extracted_named_entities = extract_named_entities(user_input)
            query_extracted_named_entities.set(extracted_named_entities)
            
            # TODO # Implement context retrieval

            retrieved_context = "The meaninig of life is 42"
            result = answer_query(user_input, context=retrieved_context)
            # Append a response to the chat
            await chat.append_message(f"Savant said: {result.raw}")
