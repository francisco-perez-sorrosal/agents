import json


from crewai import Agent, Crew, Process
from crewai.crews import CrewOutput
from llm_foundation.agent_types import Persona, Role

from hackathon.input_output_types import DocumentStructures
from hackathon.tools import read_file, create_matrix_entity_ref_count

from llm_foundation import logger


entity_master = Persona.from_yaml_file("Personas/EntityMasterCrewAI.yaml")
file_reader_role: Role = entity_master.get_role("file_reader")
matrix_creator_role: Role = entity_master.get_role("matrix_creator")


file_reader_agent: Agent = file_reader_role.to_crewai_agent(verbose=True,
                                                               allow_delegation=False,
                                                               allow_code_execution=False,
                                                               tools=[read_file],)
file_reader_task = file_reader_role.get_crew_ai_task("read_file", 
                                                     file_reader_agent, 
                                                     tools=[read_file], #)
                                                     output_json=DocumentStructures,)

matrix_creator_agent: Agent = matrix_creator_role.to_crewai_agent(verbose=True,
                                                              allow_delegation=False,
                                                              allow_code_execution=False,
                                                              tools=[create_matrix_entity_ref_count])
create_matrix_task = matrix_creator_role.get_crew_ai_task("create_matrix", 
                                                         matrix_creator_agent, 
                                                         tools=[create_matrix_entity_ref_count], #)
) #output_json=XXXX,)

crew = Crew(
    agents=[file_reader_agent, matrix_creator_agent], 
    tasks=[file_reader_task, create_matrix_task],
    process=Process.sequential,  # Sequential task execution
)

# Kick off the process with the Python problem as input
document_name: str = "2405.14831v1.pdf"
document_structure_file = f"{document_name.rsplit(".", 1)[0]}_document_structure_with_ne.pkl"
entity2uid_dict_file = f"{document_name.rsplit(".", 1)[0]}_entity2uid_dict.pkl"
crew_inputs = {'filename': [document_structure_file],}

result: CrewOutput = crew.kickoff(inputs=crew_inputs,)

# Present results
logger.info("------------------------------------------------------------------------------------")
file_content = json.loads(json.dumps(result.json))
logger.info(f"Type of file content: {type(file_content)}")
logger.info(file_content)
logger.info("------------------------------------------------------------------------------------")
