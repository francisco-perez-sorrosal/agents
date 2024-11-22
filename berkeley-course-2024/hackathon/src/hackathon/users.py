from typing import List, Optional

from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, listen, start, router
from crewai.crews import CrewOutput
from pydantic import BaseModel
from rich.pretty import pprint

from hackathon.graph_graphiti import GraphitiSearchTool
from llm_foundation.agent_types import Persona, Role
from llm_foundation import logger


class User(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = None
    
    def is_identified(self) -> bool:
        return self.name is not None and self.last_name is not None
    
    def __str__(self):
        if self.is_identified():
            return f"{self.name} {self.last_name}"
        elif self.name is not None or self.last_name is not None:
            return "User partially identified"
        else:
            return "User not identified"


class UserIdentityOutput(BaseModel):
    name: Optional[str] = None
    last_name: Optional[str] = None    
    user_identified: bool = False
    question: Optional[str] = None


class UserIdentityValidationState(BaseModel):
    user_info: List[str] = []
    name: Optional[str] = None
    last_name: Optional[str] = None    
    user_identified: bool = False
    question: Optional[str] = None

    def user_context(self) -> str:
        return "\n".join(self.user_info)
    
    def get_extracted_user(self) -> User:
        # assert self.user_identified and self.name is not None and self.last_name is not None, f"User not identified: {self}"
        return User(name=self.name, last_name=self.last_name)
    
    
class UserIdentificationFlow(Flow[UserIdentityValidationState]):
    
    def __init__(self, persona_file: str = "notebooks/PersonasCrewAI.yaml"):
        super().__init__()
        entity_master = Persona.from_yaml_file(persona_file)

        self.profiler_role: Role = entity_master.get_role("profiler")
        self.graphiti_finder_role: Role = entity_master.get_role("graphiti_finder")

        pprint(self.profiler_role)
        pprint(self.graphiti_finder_role)

        self.profiler: Agent = self.profiler_role.to_crewai_agent(verbose=True, allow_delegation=True,) #, tools=human_tools)
        self.graphiti_finder: Agent = self.graphiti_finder_role.to_crewai_agent(verbose=True, allow_delegation=True, tools=[GraphitiSearchTool()])
        
    @start()
    def entry_point(self):
        return "router"
    
    @router(entry_point)
    def router(self):
        if not self.state.user_identified:
            return "go_identify_user"
        else:
            return "go_validate_user"
        
    @listen("go_identify_user")
    def identify_user(self):
        identify_user = Task(
            description=self.profiler_role.tasks[0].description,
            expected_output=self.profiler_role.tasks[0].expected_output,
            agent=self.profiler,
            output_pydantic=UserIdentityOutput,    
        )

        profiler_crew = Crew(
            agents=[self.profiler],
            tasks=[identify_user],
            verbose=True,
            memory=True,
            process=Process.sequential,
            cache=False,
        )        
        user_context = self.state.user_context()
        logger.info(f"Identifying user! Context:\n{user_context}")
        crew_output: CrewOutput = profiler_crew.kickoff(inputs={"user_context": user_context})
        result: UserIdentityOutput = crew_output.pydantic
        self.state.name = result.name
        self.state.last_name = result.last_name
        self.state.user_identified = result.user_identified
        self.state.question = result.question
        if result.question is not None:
            self.state.user_info.append(result.question)
        
        # pprint(crew_output)

    @listen("go_validate_user")
    def validate_user(self):
        logger.info("Validating user in DB!!!!")
    
        logger.info(f"Identifying user! State:\n{self.state}")

        
        search_task = Task(
            description=self.graphiti_finder_role.tasks[0].description,
            expected_output=self.graphiti_finder_role.tasks[0].expected_output,
            agent=self.graphiti_finder,
        )

        # Create Crew with memory enabled
        crew = Crew(
            agents=[self.graphiti_finder],
            tasks=[search_task],
            process=Process.sequential,
            verbose=True,
        )

        logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Calling Agents ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
        result: CrewOutput = crew.kickoff(inputs={"query": f"{self.state.name} {self.state.last_name}"})
        logger.info(".................................................................................")
        logger.info(f"Answer:\n{print(result.raw)}")
        logger.info(".................................................................................")        
            
            