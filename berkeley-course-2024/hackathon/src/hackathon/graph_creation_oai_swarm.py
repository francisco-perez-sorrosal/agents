import json
from swarm import Swarm, Agent, Response
from swarm.repl import run_demo_loop
from langchain_core.prompts import PromptTemplate

from llm_foundation import logger

from llm_foundation.basic_structs import Provider, LMConfig
from llm_foundation.agent_types import Persona, Role

from hackathon.tools import load_pdf, split_text


def pretty_print_messages(messages) -> None:
    for message in messages:
        if message["role"] != "assistant":
            continue

        # print agent name in blue
        print(f"\033[94m{message['sender']}\033[0m:", end=" ")

        # print response, if any
        if message["content"]:
            print(message["content"])

        # print tool calls in purple, if any
        tool_calls = message.get("tool_calls") or []
        if len(tool_calls) > 1:
            print()
        for tool_call in tool_calls:
            f = tool_call["function"]
            name, args = f["name"], f["arguments"]
            arg_str = json.dumps(json.loads(args)).replace(":", "=")
            print(f"\033[95m{name}\033[0m({arg_str[1:-1]})")


text = load_pdf()
chunks = split_text(text)
# logger.info(chunks)
logger.info(len(chunks))
logger.info("------------")

entity_master = Persona.from_yaml_file("Personas/EntityMaster.yaml")

# logger.info(entity_master.to_yaml())

entity_extractor_role = entity_master.get_role("entity_extractor")
triple_extractor_role = entity_master.get_role("triple_extractor")

swarm_client = Swarm()


# Transfer functions

def router_function(context_variables: dict):
    """Transfer to entity extractor if not named entities in context variables. Otherwise, transfer to triple extractor."""
    if context_variables.get("named_entities", None) is None:
        print("Transfer to entity extractor")
        return entity_extractor_agent
    elif context_variables.get("triples", None) is None:
        return triple_extractor_agent
    else:
        return "Done"

def transfer_back_to_router(context_variables: dict):
    """Call this function after finishing each subtask."""
    return router_agent

 #### Agents ####
 
router_agent = Agent(
    name="Router_Agent",
    instructions=f"""You are an expert triaging users requests, and coordinating calling tools to transfer 
    each time to the agent with the right intent.
    Once you are ready to transfer to the right intent, call the tool to transfer to the right intent.
    You dont need to know specifics, just the topic of the request.
""",
    parallel_tool_calls=False
)
entity_extractor_agent = Agent(
    name=entity_extractor_role.name,
    instructions=entity_extractor_role.agent_system_message,
    parallel_tool_calls=False
)

def triple_extractor_prompt_builder(context_variables: dict) -> str:
    # print(f"PROMPT:\n{triple_extractor_role.agent_system_message}")
    prompt_template = PromptTemplate.from_template(triple_extractor_role.agent_system_message)
    original_text = context_variables.get("original_text", None)
    named_entities = context_variables.get("named_entities", None)
    example = triple_extractor_role.examples[0]
    if named_entities is None:
        return "You need to extract entities first."
    instructions = prompt_template.format(example=example, text=original_text, named_entities=named_entities) 
    # print(f"INSTRUCTIONS:\n{instructions}")
    return instructions

triple_extractor_agent = Agent(
    name=triple_extractor_role.name,
    instructions=triple_extractor_prompt_builder,
    parallel_tool_calls=False
)

router_agent.functions = [router_function] #[transfer_to_entity_extractor_agent, transfer_to_triple_extractor_agent]
entity_extractor_agent.functions.append(transfer_back_to_router)
triple_extractor_agent.functions.append(transfer_back_to_router)


text = ""
for chunk in chunks:
    text += chunk.page_content


task = f"""
Follow the plan below step by step:

1. If there are not named entities extracted, extract them from the text below.
2. With the extracted named entities and the original text, extract triples.

Text: ```{text}```

Do not finish till the JSON object in the response includes both, the extracted entities and triples. Don't use markdown.
"""


message = {"role": "user", "content": task}
agent = router_agent
logger.info(f"First Agent: {agent.name}")

messages = []
ctx_variables = {"original_text": text}

hast_triples = ctx_variables.get("triples", None)

while hast_triples is None:
    logger.info("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    messages.append(message)
    logger.info(f"Messages: {len(messages)}")
    # for message in messages:
    #     if message.get("content", None) is not None:
    #         logger.info(f"Message: {message['content']}\n\n")
    #     else:
    #         logger.info(f"Message: {message}\n\n")
    response = swarm_client.run(
        agent, 
        messages=messages, 
        context_variables=ctx_variables,
        debug=False)


    agent = response.agent
    logger.info(f"Last Agent: {agent.name}")
    if agent.name == "Entity_Extractor":
        named_entities = json.loads(response.messages[-1]["content"]).get('named_entities', None)
        if named_entities is not None:
            logger.info("Named entities extracted!!! Continue to triple extractor")
            ctx_variables["named_entities"] = named_entities
        else:
            logger.warning("No named entities!!! Continue to router agent")
        agent = router_agent
    if agent.name == "Triple_Extractor":
        triples = json.loads(response.messages[-1]["content"]).get('triples', None)
        if triples is not None:
            logger.info("Triples extracted!!! Continue to triple extractor")
            ctx_variables["triples"] = triples
        else:
            logger.warning("No triples!!! Continue to router agent")
            agent = router_agent
    pretty_print_messages(response.messages)
    logger.info("------------------------------------------------")
    hast_triples = json.loads(response.messages[-1]["content"]).get('triples', None)


# n_of_msgs = len(response.messages)
# for i in range(n_of_msgs):
#     logger.info(f"************** {response.messages[i]["role"]} msg {i} **************")
#     if response.messages[i]['role'] == "tool":
#         logger.info(f"Tool msg on tool {response.messages[i]['tool_name']}")
#     else:
#         logger.info(f"Message sent by {response.messages[i]["sender"]}:")
#     logger.info(response.messages[i]["content"])


logger.info("------------+++++++++++++++------------")

import json

json_ob = json.loads(response.messages[-1]["content"])

import pprint

pprint.pprint(json_ob, indent=2)
