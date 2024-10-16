from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
from autogen import Agent, UserProxyAgent, ConversableAgent, AssistantAgent, GroupChat, GroupChatManager
from autogen.code_utils import content_str
import math
import os
import sys
from pprint import pprint

# See this for self execution agent
# It won't work bc used openai v. < 1 and now autogen uses openai v. > 1
# https://gist.github.com/bonadio/96435a1b6ccc32297aa8cc1db7cfc381


def load_restaurant_data() -> Dict[str, List[str]]:
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
    
    return restaurant_reviews

# Load the restaurant data once
RESTAURANT_DATA = load_restaurant_data()

def fetch_restaurant_data(restaurant_name: str) -> Dict[str, List[str]]:
    try:
        return {restaurant_name: RESTAURANT_DATA[restaurant_name]}
    except KeyError:
        print(f"Restaurant {restaurant_name} not found!")
        return {restaurant_name: []}

def fetch_restaurant_names() -> List[str]:
    return list(RESTAURANT_DATA.keys())
    

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

    # example LLM config for the entrypoint agent
    llm_config = {"config_list": [{"model": "gpt-4o-mini", "api_key": os.environ.get("OPENAI_API_KEY")}]}
    print(llm_config)
    # the main entrypoint/supervisor agent
    
    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        code_execution_config={"last_n_messages": 20, "work_dir": "coding", "use_docker": False},
        is_termination_msg=lambda msg: msg.get("content", "").find("TERMINATE") >= 0,
        description="Never select me as a speaker."
    )

    ###########################################################################
    ### Restaurant Fetcher Agent
    ###########################################################################

    restaurant_fetcher_agent_system_message = """
    You excel at fetching review data for restaurants, invoking the necessary tools available when required.
    From the user request, fetch the reviews for the restaurant specified. If you get an empty list [] of reviews when 
    fetching the restaurant data, the name of the restaurant was probably mispelled. 
    In this case, fetch the list of available restaurant names and try 
    to get the reviews again choosing the closest restaurant name to the original one.    
    Do not return an empty list []. Return only a list filled with user reviews of the restaurant.
    """        
    restaurant_data_fetcher = AssistantAgent(
        name="Restaurant_Data_Fetcher",
        system_message=restaurant_fetcher_agent_system_message,
        llm_config=llm_config,
        max_consecutive_auto_reply=20,
        # description="""I am **ONLY** allowed to speak **immediately** after `User` or `Restaurant_Data_Fetcher`.
        # If `Restaurant_Data_Fetcher` returns a tool call with an empty list [], the next speaker must be `Restaurant_Data_Fetcher` again.
        # """,
    )
    restaurant_data_fetcher.register_for_execution(name="fetch_restaurant_data")(fetch_restaurant_data)
    restaurant_data_fetcher.register_for_execution(name="fetch_restaurant_names")(fetch_restaurant_names)            
    restaurant_data_fetcher.register_for_llm(name="fetch_restaurant_data", description="Fetches the user reviews for a specific restaurant.")(fetch_restaurant_data)
    restaurant_data_fetcher.register_for_llm(name="fetch_restaurant_names", description="Fetches the names of available restaurants.")(fetch_restaurant_names)    
    
    
    ###########################################################################
    ### Review Organizer Agent
    ###########################################################################
    
    review_extractor_agent_system_message = """
    You are an expert in extracting and organizing reviews for restaurants from structured data.
    
    From a JSON object with the following format:
           
    { "Restaurant Name": ["Review 1", "Review 2", ..., "Review N"] }
    
    in which "Restaurant Name" and "Review 1" ... "Review N" are of type <string>.

    Traverse the list of reviews one by one and enumerate -starting with index 0- all reviews with the following format:
    
    <integer>: <review>    
    """
    review_organizer_agent = ConversableAgent(
        name="Review_Organizer_Agent",
        system_message=review_extractor_agent_system_message,
        llm_config=llm_config,
        description="""I am **ONLY** allowed to speak **immediately** after `Restaurant_Data_Fetcher`"""
    )
 
    ###########################################################################
    ### Review Scorer Agent
    ###########################################################################
    
    review_scorer_agent_system_message = """
    You wil receive a list of reviews with the format:
    
    <integer>: <review_as_string>
    
    where <integer> is a sequence from 1 to N.
    
    For every review, extract two scores:

    1) food_score: the quality of food at the restaurant. Graded from 1-5.
    2) customer_service_score: the quality of customer service at the restaurant. Also graded from 1-5.
    
    Assign these scores paying attention at keywords in each review. Specially each review has keyword 
    adjectives that correspond to the score that the restaurant should get for its food_score and 
    customer_service_score. 
    
    Here are the keywords the agent should look out for:

    - Score 1/5 has one of these adjectives: awful, horrible, or disgusting.
    - Score 2/5 has one of these adjectives: bad, unpleasant, or offensive.
    - Score 3/5 has one of these adjectives: average, uninspiring, or forgettable.
    - Score 4/5 has one of these adjectives: good, enjoyable, or satisfying.
    - Score 5/5 has one of these adjectives: awesome, incredible, or amazing.
    
    Each review will have exactly only two of these keywords (adjective describing food and 
    adjective describing customer service), and the score (N over 5) is only determined through the
    above listed keywords. No other factors go into score extraction. 
    
    To illustrate the concept of scoring better, here's an example review:
    
    'The food at McDonald's was average, but the customer service was unpleasant. 
    The uninspiring menu options were served quickly, but the staff seemed disinterested
    and unhelpful.'
    
    In this case the food is described as "average", which corresponds to a food_score of 3. 
    The customer service is described as "unpleasant", which corresponds 
    to a customer_service_score of 2. Therefore, you must assign 
    food_score: 3 and customer_service_score: 2 for this example review.
    
    Reply enumerating carefully each review again and for each:
    
    1. Extract explicitly the keywords corresponding to food and customer service
    2. Based on the keywords extracted, create the score for food and customer service for that entry
    
    """
    review_scorer_agent = ConversableAgent(
        name="Review_Scorer_Agent",
        system_message=review_scorer_agent_system_message,
        llm_config=llm_config,
        # description="""I am **ONLY** allowed to speak **immediately** after `Review_Organizer_Agent`"""
    )
    
    ###########################################################################
    ### Review Formater Agent
    ###########################################################################
    
    review_formatter_agent_system_message = """
    For each user review for a restaurant, aggregate the food and customer service results in order and return a JSON object with this format:
    
    {
        'food_scores': [food_score_review_1, food_score_review_2, food_score_review_3, ..., food_score_review_N], 
        'customer_service_scores': [customer_service_score_review_1, customer_service_score_review_2, customer_service_score_review_3, ..., customer_service_score_review_N]
    }
    
    Just return the raw JSON object.
    """
    review_formatter_agent = ConversableAgent(
        name="Review_Formatter_Agent",
        system_message=review_formatter_agent_system_message,
        llm_config=llm_config,
        # description="""I am **ONLY** allowed to speak **immediately** after `Review_Scorer_Agent`"""
    )    
    
    ###########################################################################
    ### Overall Scoring Agent
    ###########################################################################
    overall_scoring_agent_system_message = """
    Calculate an overall score for the restaurant from the review scores of food and customer service data.
    If the final score doesn't have at least three decimals, complete with zeros up to three decimals.
    Provide the answer with 3 decimals and return 'TERMINATE' when the task is done.
    """
    overall_scoring_agent = ConversableAgent(
        name="Overall_Scoring_Agent",
        system_message=overall_scoring_agent_system_message,
        llm_config=llm_config,
        max_consecutive_auto_reply=8,
        human_input_mode="NEVER",
        description = """I am **ONLY** allowed to speak **immediately** after `Review_Formatter_Agent` or `Overall_Scoring_Agent`.
        If `Overall_Scoring_Agent` returns a tool call, the next speaker must be `Overall_Scoring_Agent` again.
        """
    )
    overall_scoring_agent.register_for_llm(name="calculate_overall_score", description="From the individual scores of food and custormer service data, it calculates an overall score for a restaurant.")(calculate_overall_score)
    overall_scoring_agent.register_for_execution(name="calculate_overall_score")(calculate_overall_score)

 
    def find_last_tool_call_pair(messages: List[Dict]) -> Optional[Tuple[str, str]]:
        function_calls = []
        for message in reversed(messages):
            
            tool_call = message.get("tool_calls", None)
            if tool_call is not None:
                function_calls.append(tool_call[-1]["function"]["name"])
            if len(function_calls) == 2:
                return tuple(reversed(function_calls))
        return None if len(function_calls) < 2 else tuple(reversed(function_calls))

 
    def speaker_selection_fn(last_speaker: Agent, groupchat: GroupChat):
        """Define a customized speaker selection function.
        A recommended way is to define a transition for each speaker in the groupchat.

        Returns:
            Return an `Agent` class or a string from ['auto', 'manual', 'random', 'round_robin'] to select a default method to use.
        """
        messages = groupchat.messages
        print(f"Len messages: {len(messages)}")
        last_message = messages[-1]
        print("/" * 100)
        print(f"Last speaker: {last_speaker.name}")
        print(f"Last msg: {last_message}")
        
        #######################################################################
        # Restaurant_Data_Fetcher tweaks
        #######################################################################
        
        # Force Restaurant_Data_Fetcher stay after last tool call returned an empty list
        if (last_speaker.name == "Restaurant_Data_Fetcher" and  len(messages) == 3 and last_message["role"] == 'tool' and "[]" in last_message["content"]):
            print("Empty list found")
            return last_speaker
        # Also force Restaurant_Data_Fetcher to stay once more after last tool call pattern: 'fetch_restaurant_data' -> [] -> 'fetch_restaurant_names'
        if last_speaker.name == "Restaurant_Data_Fetcher" and last_message["role"] == 'tool':
            last_function_pair = find_last_tool_call_pair(messages)
            if last_function_pair:
                print(f"Last Function Pair (prev2last, last): {last_function_pair}")                
                # This means that the Restaurant_Data_Fetcher still hasn't done its job,
                # so it's still exploring restaurant names
                if last_function_pair == ('fetch_restaurant_data', 'fetch_restaurant_names'):
                    print(f"Keeping next speaker as {last_speaker.name}")
                    return last_speaker

        #######################################################################
        # Overall_Scoring_Agent tweaks
        #######################################################################

        # Force Overall_Scoring_Agent stay after last tool call to produce a human-readable result after tool call
        if last_speaker.name == "Overall_Scoring_Agent" and last_message["role"] == 'tool':
            return last_speaker
        print("/" * 100)
        return "auto"
    
    agents=[user_proxy, restaurant_data_fetcher, review_organizer_agent,  review_scorer_agent, review_formatter_agent, overall_scoring_agent]
        
    groupchat = GroupChat(agents=agents, 
                          messages=[], 
                          max_round=16,
                          speaker_selection_method=speaker_selection_fn,  # or "auto"
                          send_introductions=True,
                          allow_repeat_speaker=True,
                          )

    lab1_manager_system_message = """
    You are an evaluator of fast-food restaurants. 
    When you have all the information, return the final answer and 'TERMINATE'.
    """
    lab1_manager = GroupChatManager(groupchat=groupchat,
                                    name="Lab1_Manager",
                                    system_message=lab1_manager_system_message,
                                    is_termination_msg=lambda msg: content_str(msg.get("content")).find("TERMINATE") >= 0,
                                    )
    
    # Here starts everythiing
    result = user_proxy.initiate_chat(
        lab1_manager, 
        message=user_query
    )

    print("=" * 100)
    pprint(result.chat_history)
    print("=" * 100)
    
# DO NOT modify this code below.
if __name__ == "__main__":
    assert len(sys.argv) > 1, "Please ensure you include a query for some restaurant when executing main."
    main(sys.argv[1])
    
    # from dotenv import find_dotenv, load_dotenv
    # load_dotenv(find_dotenv())
    # try:
    #     assert len(sys.argv) > 1, "Please ensure you include a query for some restaurant when executing main."
    #     user_query = sys.argv[1]
    # except AssertionError as e:
    #     user_query = "What is the overall score for taco bell?"
    #     user_query = "What is the overall score for In N Out?"
    #     # user_query = "How good is the restaurant Chick-fil-A overall?"
    # main(user_query)
