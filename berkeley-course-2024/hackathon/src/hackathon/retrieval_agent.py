import json

import os
from typing import Any, Dict, List, Literal, Optional

from llm_foundation import logger
from llm_foundation.agent_types import Persona, Role

from crewai import Agent, Task, Crew
from crewai.crews import CrewOutput
from langchain.output_parsers.json import SimpleJsonOutputParser
from rich.pretty import pprint
from hackathon.input_output_types import NamedEntities


def extract_named_entities(user_query: str) -> List[str]:
    print(os.getcwd())
    entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
    entity_extractor_role: Role = entity_master.get_role("entity_extractor")
    pprint(entity_extractor_role)
    entity_extractor: Agent = entity_extractor_role.to_crewai_agent(verbose=True, allow_delegation=False)

    extract_entities = entity_extractor_role.get_crew_ai_task("extract_entities", entity_extractor, output_json=NamedEntities)

    query_inputs = {
        "paragraph": user_query,
        # "paragraph": "What is HippoRAG?",
        "entity_extractor_examples": entity_extractor_role.get_examples_as_str(),
    }

    crew = Crew(
        agents=[entity_extractor],
        tasks=[extract_entities],
        verbose=True,
    )

    logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Calling Agents ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    result: CrewOutput = crew.kickoff(inputs=query_inputs)
    logger.info(".................................................................................")
    logger.info(type(result.json))
    logger.info(result)
    entities = json.loads(result.json)
    return entities["named_entities"]


def answer_query(user_query: str, context: Optional[str] = None) -> CrewOutput:
    entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
    hippo_savant_role: Role = entity_master.get_role("hippo_savant")
    hippo_savant: Agent = hippo_savant_role.to_crewai_agent(verbose=True, allow_delegation=False)

    answer_question = hippo_savant_role.get_crew_ai_task("answer_question", hippo_savant)

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
    logger.info(".................................................................................")
    return result
