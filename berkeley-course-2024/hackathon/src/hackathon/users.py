from typing import List, Optional
import uuid

import numpy as np

from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, listen, start, router
from crewai.crews import CrewOutput
from crewai_tools import tool
from pydantic import BaseModel
from rich.pretty import pprint
from hackathon.graph_graphiti import GraphitiSearchTool
from hackathon.index import generate_embeddings
from hackathon.tools import graphdb_retrieval_tool
from hackathon.utils import Neo4jClientFactory
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

        self.profiler: Agent = self.profiler_role.to_crewai_agent(verbose=True, allow_delegation=True,)
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
            

class UserCreationCrew():
    def __init__(self):
        self.user_db_persona = Persona.from_yaml_file("notebooks/UserDBCrewAI.yaml")

        self.entity_retriever_role: Role = self.user_db_persona.get_role("entity_retriever")
        self.user_manager_role: Role = self.user_db_persona.get_role("user_manager")

        self.entity_retriever: Agent = self.entity_retriever_role.to_crewai_agent(verbose=True, allow_delegation=True, tools=[graphdb_retrieval_tool] )
        self.user_manager: Agent = self.user_manager_role.to_crewai_agent(verbose=True, allow_delegation=True, tools=[graphdb_add_user_tool])
        
    def create_user(self, state: UserIdentityValidationState) -> CrewOutput:

        retrieve_entity = Task(
            description=self.entity_retriever_role.tasks[0].description,
            expected_output=self.entity_retriever_role.tasks[0].expected_output,
            agent=self.entity_retriever,
        )

        add_user = Task(
            description=self.user_manager_role.tasks[0].description,
            expected_output=self.user_manager_role.tasks[0].expected_output,
            agent=self.user_manager,
        )


        manager = Agent(
            role="User Creator",
            goal="Efficiently manage the crew and ensure high-quality task completion",
            backstory="You're an database manager, skilled in overseeing complex task workflows to add users to a database and guiding your teams to success. Your role is to coordinate the efforts of the crew members, ensuring that each task is completed on time and to the highest standard.",
            allow_delegation=True,
        )

        profiler_crew = Crew(
            agents=[self.entity_retriever, self.user_manager],
            tasks=[retrieve_entity, add_user],
            manager_agent=manager,
            planning=True,
            verbose=True,
            memory=True,
            process=Process.sequential,
            cache=False,
        )

        user_inputs = {
            "entity_context": str(state.get_extracted_user()),  # Input the full name as a string
            "user_context": state.user_context(),  # Input the raw Pydantic object
        }
        crew_output: CrewOutput = profiler_crew.kickoff(inputs=user_inputs)
        return crew_output

#### User Database ####

def add_users(neo4j_factory: Neo4jClientFactory, embeddings: np.ndarray, users: List[User]):
    kg = neo4j_factory.langchain_client()
    
    all_users = []
    for user, emb in zip(users, embeddings):
        uuid_text = f"{user.name} {user.last_name}"
        generated_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, uuid_text))
        all_users.append({"uid": generated_uuid, "type": "user", "name": user.name, "last_name": user.last_name, "embedding": emb})

    print(f"Number of users to add: {len(all_users)}")

    query = """
    UNWIND $all_users AS au
    MERGE (a:Entity {node_id: au.uid, type: au.type, name: au.name, last_name: au.last_name, embedding: au.embedding})
    """
    kg.query(query, {"all_users": all_users})


###################################################################################################
# Crew AI tools
###################################################################################################

def graphdb_add_user(user: User, embedding):
    neo4j_factory = Neo4jClientFactory()
    print(f"Factory: {neo4j_factory}")
    add_users(neo4j_factory, embedding, [user])  #Fix here the emb_dim


@tool
def graphdb_add_user_tool(name: str, last_name: str) -> bool:
    """Adds a user to the graph database.
    """
    try:
        user = User(name=name, last_name=last_name)
        embedding = generate_embeddings([str(user)])
        # print(f"Embedding: {embedding}")
        graphdb_add_user(User(name=name, last_name=last_name), embedding)
        return True
    except Exception as e:
        print(f"Error adding user {user}: {e}")
        return False
