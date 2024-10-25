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
ATTENTION (INTENTIONAL BREAK): Fill out YOUR SPECIFIC VALUES for the env variables in `env.example` and then:
mv env.example .env

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
# Step 2: Run agent for final graph creation
#######################################################################
pixi run python src/hackathon/grap_creation_step_3.py
```

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
