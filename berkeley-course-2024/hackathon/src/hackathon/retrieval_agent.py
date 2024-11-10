from typing import Any, Dict, List, Literal, Optional

from llm_foundation import logger
from llm_foundation.agent_types import Persona, Role

from crewai import Agent, Task, Crew
from crewai.crews import CrewOutput
from langchain.output_parsers.json import SimpleJsonOutputParser
from rich.pretty import pprint


def answer_query(user_query: str, context: Optional[str] = None) -> CrewOutput:
    entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")

    hippo_savant_role: Role = entity_master.get_role("hippo_savant")
    hippo_savant: Agent = hippo_savant_role.to_crewai_agent(verbose=True, allow_delegation=False)

    answer_question = Task(
        description=hippo_savant_role.tasks[0].description,
        expected_output=hippo_savant_role.tasks[0].expected_output,
        agent=hippo_savant,
    )

    query_inputs = {
        "context": context if context else "",
        "query": user_query,
    }

    crew = Crew(
        agents=[hippo_savant],
        tasks=[answer_question],
        verbose=True,
    )

    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Calling Agents ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    result: CrewOutput = crew.kickoff(inputs=query_inputs)
    return result


result = answer_query("What is the meaning of life?")

logger.info(".................................................................................")
logger.info(f"Answer:\n{pprint(result.raw)}")
logger.info(".................................................................................")
