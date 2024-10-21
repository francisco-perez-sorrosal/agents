from swarm import Swarm, Agent

from llm_foundation import logger

from llm_foundation.basic_structs import Provider, LMConfig
from llm_foundation.agent_types import Persona, Role

francisco = Persona.from_json_file("Personas/Francisco.json")

logger.info(francisco)
logger.info(francisco.get_roles())



client = Swarm()

def transfer_to_spanish_agent():
    """Transfer spanish speaking users immediately."""
    return agent_b

agent_a_role: Role  = francisco.roles["agent_a"]
agent_a = Agent(
    name=agent_a_role.name,
    instructions=agent_a_role.agent_system_message,
    functions=[transfer_to_spanish_agent],
)

agent_b_role: Role  = francisco.roles["agent_b"]
agent_b = Agent(
    name=agent_b_role.name,
    instructions=agent_b_role.agent_system_message,
)

response = client.run(
    agent=agent_a,
    messages=[{"role": "user", "content": "Hola. ¿Como se traduce hola al ingles?"}],
)

# print(response)

n_of_msgs = len(response.messages)
for i in range(n_of_msgs):
    logger.info(f"************** {response.messages[i]["role"]} msg {i} **************")
    if response.messages[i]['role'] == "tool":
        logger.info(f"Tool msg on tool {response.messages[i]['tool_name']}")
    else:
        logger.info(f"Message sent by {response.messages[i]["sender"]}:")
    logger.info(response.messages[i]["content"])
