from typing import Dict, List
from autogen import UserProxyAgent, ConversableAgent, AssistantAgent
import math
import os
import sys

def fetch_restaurant_data(restaurant_name: str) -> Dict[str, List[str]]:
    # TODO
    # This function takes in a restaurant name and returns the reviews for that restaurant. 
    # The output should be a dictionary with the key being the restaurant name and the value being a list of reviews for that restaurant.
    # The "data fetch agent" should have access to this function signature, and it should be able to suggest this as a function call. 
    # Example:
    # > fetch_restaurant_data("Applebee's")
    # {"Applebee's": ["The food at Applebee's was average, with nothing particularly standing out.", ...]}
    restaurant_reviews = {}
    
    with open("restaurant-data.txt", 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            name, review = line.split('. ', 1)
            if name in restaurant_reviews:
                restaurant_reviews[name].append(review)
            else:
                restaurant_reviews[name] = [review]
    
    # print(f"The restaurant dict has {len(restaurant_reviews)} entries.")
    # for name, _ in restaurant_reviews.items():
    #     print(f"{name}: {len(restaurant_reviews[name])} reviews")
        
    return {restaurant_name: restaurant_reviews[restaurant_name]}


def calculate_overall_score(restaurant_name: str, food_scores: List[int], customer_service_scores: List[int]) -> Dict[str, float]:
    # TODO
    # This function takes in a restaurant name, a list of food scores from 1-5, and a list of customer service scores from 1-5
    # The output should be a score between 0 and 10, which is computed as the following:
    # SUM(sqrt(food_scores[i]**2 * customer_service_scores[i]) * 1/(N * sqrt(125)) * 10
    # The above formula is a geometric mean of the scores, which penalizes food quality more than customer service. 
    # Example:
    # > calculate_overall_score("Applebee's", [1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    # {"Applebee's": 5.048}
    # NOTE: be sure to that the score includes AT LEAST 3  decimal places. The public tests will only read scores that have 
    # at least 3 decimal places.
    if len(food_scores) != len(customer_service_scores):
        raise ValueError("The lengths of food_scores and customer_service_scores must be the same.")
    
    N = len(food_scores)
    sum_geometric_means = 0
    
    for i in range(N):
        geometric_mean = math.sqrt(food_scores[i]**2 * customer_service_scores[i])
        sum_geometric_means += geometric_mean
    
    overall_score = (sum_geometric_means / (N * math.sqrt(125))) * 10
    overall_score = round(overall_score, 3)
        
    return {restaurant_name: overall_score}

def get_data_fetch_agent_prompt(restaurant_query: str) -> str:
    # TODO
    # It may help to organize messages/prompts within a function which returns a string. 
    # For example, you could use this function to return a prompt for the data fetch agent 
    # to use to fetch reviews for a specific restaurant.
    pass

# TODO: feel free to write as many additional functions as you'd like.

# Do not modify the signature of the "main" function.
def main(user_query: str):
    # TODO Implement the system message.
    entrypoint_agent_system_message = """
    You critic of fast-food restaurants. 
    You will receive questions from users about a restaurant and you will answer them.
    """
    # example LLM config for the entrypoint agent
    llm_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")}]}
    # the main entrypoint/supervisor agent
    entrypoint_agent = ConversableAgent("entrypoint_agent", 
                                        system_message=entrypoint_agent_system_message,
                                        is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],  # Added by FPS
                                        human_input_mode="NEVER",  # Added by FPS
                                        max_consecutive_auto_reply=1,
                                        llm_config=llm_config)
    # entrypoint_agent.register_for_llm(name="fetch_restaurant_data", description="Fetches the reviews for a specific restaurant.")(fetch_restaurant_data)
    entrypoint_agent.register_for_execution(name="fetch_restaurant_data")(fetch_restaurant_data)
    # fetch_restaurant_data("Applebee's")
    # print(calculate_overall_score("Applebee's", [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]))
    

    # TODO
    # Create more agents here.
    data_fetch_agent_system_message = """
    Fetch the review data for a restaurant.
    Return 'TERMINATE' when the task is done.
    """
    data_fetch_agent = ConversableAgent(
        name="Data Fetch Agent",
        system_message=data_fetch_agent_system_message,
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
        human_input_mode="NEVER",
    )
    data_fetch_agent.register_for_llm(name="fetch_restaurant_data", description="Fetches the reviews for a specific restaurant.")(fetch_restaurant_data)
    # data_fetch_agent.register_for_execution(name="fetch_restaurant_data")(fetch_restaurant_data)
    
    # print(f"Tools: {data_fetch_agent.llm_config['tools']}")
    
    review_extractor_agent_system_message = """
    You are an expert in analyzing reviews for restaurants.
    
    You receive a JSON object with the following format:
           
    { "Restaurant Name": ["Review 1", "Review 2", ..., "Review N"] }
    
    "Restaurant Name" and "Review 1" ... "Review N" are of type <string>.

    Traverse the list of reviews one by one and enumerate -starting with index 0- all reviews with the following format:
    
    <integer>: <review>    
    """
    review_analyzer_agent = ConversableAgent(
        name="Restaurant Analyzer Agent",
        system_message=review_extractor_agent_system_message,
        llm_config=llm_config,
    )

    review_scorer_agent_system_message = """
    You must look at every single review in the <integer> marked from from 1 to N, and for each one, extract two scores:

    1) food_score: the quality of food at the restaurant. This will be a score from 1-5.
    2) customer_service_score: the quality of customer service at the restaurant. This will be also a score from 1-5.
    
    You must assign these scores looking at keywords in each review. Each review has keyword adjectives that 
    correspond to the score that the restaurant should get for its food_score and customer_service_score. 
    Here are the keywords the agent should look out for:

    - Score 1/5 has one of these adjectives: awful, horrible, or disgusting.
    - Score 2/5 has one of these adjectives: bad, unpleasant, or offensive.
    - Score 3/5 has one of these adjectives: average, uninspiring, or forgettable.
    - Score 4/5 has one of these adjectives: good, enjoyable, or satisfying.
    - Score 5/5 has one of these adjectives: awesome, incredible, or amazing.
    
    Each review will have exactly only two of these keywords (adjective describing food and 
    adjective describing customer service), and the score (N/5) is only determined through the
    above listed keywords. No other factors go into score extraction. 
    
    To illustrate the concept of scoring better, here's an example review:
    
    'The food at McDonald's was average, but the customer service was unpleasant. 
    The uninspiring menu options were served quickly, but the staff seemed disinterested
    and unhelpful.'
    
    In this case the food is described as "average", which corresponds to a food_score of 3. 
    The customer service is described as "unpleasant", which corresponds 
    to a customer_service_score of 2. Therefore, you must assign 
    food_score: 3 and customer_service_score: 2 for this example review.
    
    Enumerate carefully through the reviews and for each of it:
    
    1. Extract explicitly the keywords corresponding to food and customer service
    2. Based on the keywords extracted, create the score for food and customer service for that entry
    
    """
    review_scorer_agent = ConversableAgent(
        name="Review Scorer Agent",
        system_message=review_scorer_agent_system_message,
        llm_config=llm_config,
    )

    review_formatter_agent_system_message = """
    Finally, for each review, aggregate the food and customer service results in order and return a JSON object with this format:
    
    {
        'food_scores': [food_score_review_1, food_score_review_2, food_score_review_3, ..., food_score_review_N], 
        'customer_service_scores': [customer_service_score_review_1, customer_service_score_review_2, customer_service_score_review_3, ..., customer_service_score_review_N]
    }
    
    Just return the raw JSON object.
    """
    review_formatter_agent = ConversableAgent(
        name="Review Formatter Agent",
        system_message=review_formatter_agent_system_message,
        llm_config=llm_config,
    )
        
    # Other formats
    # {
    #     'food_scores': [food_score_1, food_score_2, food_score_3, ..., food_score_N], 
    #     'customer_service_scores': [customer_service_score_1, customer_service_score_2, customer_service_score_3, ..., customer_service_score_N]
    # }

    # review, food_keywords, customer_service_keywords, food_score, customer_service_score
    
    # TODO
    # Fill in the argument to `initiate_chats` below, calling the correct agents sequentially.
    # If you decide to use another conversation pattern, feel free to disregard this code.
    
    # Uncomment once you initiate the chat with at least one agent.
    result = entrypoint_agent.initiate_chats([
        {
            "recipient": data_fetch_agent,
            "message": user_query,
            "clear_history": True,
            "silent": False,
            "max_turns": 2,
            "summary_method": "last_msg"
        },
        {
            "recipient": review_analyzer_agent,
            "message": "This is the fetched data for the restaurant.",
            "clear_history": False,
            "silent": False,
            "max_turns": 1,
            "summary_method": "last_msg"
        },
        {
            "recipient": review_scorer_agent,
            "message": "This is the list of reviews for the restaurant.",
            "clear_history": False,
            "silent": False,
            "max_turns": 1,
            "summary_method": "last_msg"
        },
        {
            "recipient": review_formatter_agent,
            "message": "This is the list to format.",
            "clear_history": False,
            "silent": False,
            "max_turns": 1,
            "summary_method": "last_msg"
        },        
    ])
    
    
    
    # print(result)
    print(len(result))
    # print(result[-1].tool_responses)
    # print(f"Last message of entrypoint agent:")
    # print(entrypoint_agent.last_message())
    # print(f"Last message of fetch agent:")
    # print(data_fetch_agent.last_message())

    print(f"Last message of review_analyzer agent:")
    print(review_analyzer_agent.last_message())
    
    result = review_analyzer_agent.last_message()
    
    # Alternative way to register the fetch_restaurant_data function with the two agents.
    # from autogen import register_function

    # register_function(
    #     fetch_restaurant_data,
    #     caller=data_fetch_agent,  # The assistant agent can suggest calls to the calculator.
    #     executor=entrypoint_agent,  # The user proxy agent can execute the calculator calls.
    #     name="fetch_restaurant_data",  # By default, the function name is used as the tool name.
    #     description="Fetches data reviews from a particular restaurant",  # A description of the tool.
    # )
    
    
# DO NOT modify this code below.
if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv())
    try:
        assert len(sys.argv) > 1, "Please ensure you include a query for some restaurant when executing main."
        user_query = sys.argv[1]
    except AssertionError as e:
        user_query = "How good is the food at McDonald's?"
    # main(sys.argv[1])
    main(user_query)