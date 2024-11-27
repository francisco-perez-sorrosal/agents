from typing import Any, Dict, List, Optional

from crewai import Agent, Crew, Process
from crewai.crews import CrewOutput
from pydantic import BaseModel, Field
from rich.pretty import pprint

from llm_foundation.agent_types import Persona, Role


class TopicReport(BaseModel):
    topics: List[str] = Field(..., description="A chronologically ordered list with different topics identified in a conversation up to now.")
    is_new_topic: bool = Field(False, description="If the last topic can be considered as a delimiter of a memory episode.")


def extract_topics(previous_topics: List[str], conversation: List[Dict]) -> TopicReport:

    topic_master = Persona.from_yaml_file("Personas/TopicCrewAI.yaml")
    topic_identifier_role: Role = topic_master.get_role("topic_identifier")
    pprint(topic_identifier_role)
    topic_identifier: Agent = topic_identifier_role.to_crewai_agent(verbose=True, allow_delegation=True,)
    identify_topic = topic_identifier_role.get_crew_ai_task("identify_topic", topic_identifier, output_pydantic=TopicReport)
    
    
    # Conversation: List of {'content': 'welcome', 'role': 'assistant'}
    print(f"Extracting topic from conversation: {conversation}\nPrevious Topics: {previous_topics}")
    content = conversation[-1]["content"]
    
    topic_extractor_crew = Crew(
        agents=[topic_identifier],
        tasks=[identify_topic],
        verbose=True,
        memory=True,
        process=Process.sequential,
        cache=False,
    )        
    
    
    
    inputs = {
        "previous_topics": previous_topics,
        "conversation": content
    }
    crew_output: CrewOutput = topic_extractor_crew.kickoff(inputs=inputs)
    result: TopicReport = crew_output.pydantic
    return result

if __name__ == "__main__":
    topic_report = extract_topics(["Neuroscience", "Memory", "Disease"], [{'content': 'welcome', 'role': 'assistant'}])
    pprint(topic_report)
    
