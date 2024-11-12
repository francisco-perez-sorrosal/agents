# Hackathon

## Install Dev Env

### Dependencies

Crew AI
Neo4j: GraphDB / Vector DB (Aura cloud)
OpenAI: GPT-4o for (LLM) and text-embedding-small

### Install

1. Install [pixi](https://pixi.sh/latest/)

2. Run project:

```sh
cd berkeley-course-2024/hackathon
pixi install
ATTENTION (INTENTIONAL BREAK): Fill out YOUR SPECIFIC VALUES for the env variables in `dot_env.example` and then:
mv dot_env.example .env

#######################################################################
# TODO The steps below are for reference and will evolve
############################ Grap Creation ############################
# Step 1: Run agent for document structure creation
#######################################################################
pixi run python src/hackathon/graph_creation_crewai.py
#######################################################################
# Step 2: Run agent for triple creation
#######################################################################
pixi run python src/hackathon/grap_creation_step_2_triples.py
#######################################################################
# Step 3: Run agent for final graph creation
#######################################################################
pixi run python src/hackathon/grap_creation_step_3.py
```

## Run Application UI

```sh
#######################################################################
# Run UI (Shiny based) and configured as a task in pyproject.toml
#######################################################################
pixi run ui
```

## Agent Observability

Implemented with [Langtrace](https://www.langtrace.ai/)
Create an account and get the Key.
**NOTE** Set the `OBSERVE_AGENTS` env variable in `.env` to False when not debugging,
as Langtrace has a limited number of traces (or spans in their nomenclature) that are
free each month. By default is also False to not to waste traces.

### Development

#### Test (Not implemented yet)

Create pytest pixi env:

```sh
pixi add --pypi --feature test pytest
pixi project environment add test --feature test --solve-group default
pixi task add --feature test pytest "pytest"
```

Once created, execute test with:

```sh
pixi r pytest
```

#### Versioning (Not implemented yet)

```sh
# Increment version
pixi project version patch
pixi install
git add .
git commit -m "xxxx < Intentional >
git push origin main
```

## Extra Reference

The stuff below is just for reference on how to use other frameworks.

```sh
pixi run python src/hackathon/basic_oai_swarm.py
pixi run python src/hackathon/graph_creation_oai_swarm.py
```

## Tech Stack

- CrewAI (Main agentic framework)
- OpenAI (gpt4o-mini is the main LLM)
- Neo4j (Main Database)
- Langtrace for monitoring: https://www.langtrace.ai/
- Shiny (https://shiny.posit.co/py/) for pythonic reactive UI
- Graphiti (For User Sessions)
- Langchain/Langraph if necessary
