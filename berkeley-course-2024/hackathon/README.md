# Hackathon

## Install Dev Env

### Dependencies

Neo4j: GraphDB / Vector DB (Aura cloud)
OpenAI: GPT-4o for (LLM) and text-embedding-small

1. Install [pixi](https://pixi.sh/latest/)

2. Run project:

```sh
cd berkeley-course-2024/hackathon
pixi install
# Run agent
pixi run python src/hackathon/basic_oai_swarm.py
pixi run python src/hackathon/graph_creation_oai_swarm.py
```

### Development

#### Test

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

#### Versioning

```sh
# Increment version
pixi project version patch
pixi install
git add .
git commit -m "xxxx < Intentional >
git push origin main
```
