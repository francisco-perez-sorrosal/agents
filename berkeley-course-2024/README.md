# Intro

Sept 9, 2024

[Course Page](https://llmagents-learning.org/f24)

[Slides](https://llmagents-learning.org/slides/intro.pdf)

## LLM Reasoning

### Denny Zhou, Google DeepMind

Sept 9, 2024

[Slides](https://llmagents-learning.org/slides/llm-reasoning.pdf)
[Talk](https://www.youtube.com/live/QL-FS_Zcmyo)
[Quiz](https://docs.google.com/forms/d/e/1FAIpQLSc2_NlSWrZZB1JZoRnVapbwAj4nxOKdlKjl_VU67i0zeomdng/viewform)
[Lab1 Stuff](https://drive.google.com/drive/folders/1mOisEUkoLBcIcdkdGDiftq4IFAJ3xpzJ)

## LLM agents: brief history and overview

### Shunyu Yao, OpenAI

Sept 16, 2024

## Agentic AI Frameworks & AutoGen

### Chi Wang, AutoGen-AI

## Building a Multimodal Knowledge Assistant

### Jerry Liu, LlamaIndex

Sept 23, 2024

## Enterprise trends for generative AI, and key components of building successful agents/applications

### Burak Gokturk, Google

Sept 30, 2024

## Compound AI Systems & the DSPy Framework

### Omar Khattab, Databricks

Oct 7, 2024

## Agents for SW Development

### Graham Neubig, CMU (and All Hands AI)

Oct 14, 2024

Maintainer of OpenHands (prev. Open Devin)

OpenHands: https://github.com/All-Hands-AI/OpenHands

#### Basic Scenarios/Papers

Simple Domains: Human Eval and MVPP
Complex Domains: CoNaLa, ODEX
Data Science Notebooks: ARCADE
SWEBench (Jimenez et al. 2023) Biased to High Quality repos. Long context understanding and precise implementations.
SWEBench+ (very new. Not in slides)
LiveCodeBench
Design2Code: MultiModal Coding Models
CodeAct (2024)
SWE-Agent (Jimenez et al. 2024)
OpenHands (Wang et al. 2024)

#### Metric: Pass@K

#### Code specialist LLMs

Train on The Stack 2 (Carefully into license)
Code Infilling: Train for code infilling
LMs are trained in relative short chunks (4096 tokens) which is good for fast training but bad for using long contexts as codebases
Copilot Prompting Strategy: Use as much as context as possible to feed into the requests to the coding tasks.
File Localization: Find the correct files given a user intent. Similar problem as understanding the environment in embodied agents. Or exploration
problems in other agents. Sol 1: Offload to the user; you must know the source code and explicitly specify the files. Sol 2: Prompt the agent with 
search tools; Sol 3: A Priory map of the repo; Aider tool (search in google for that tool) Check also Agentless (Xia et al. 2024) paper. Sol 4: Retrieva
Augmented Code Generation.

#### Planning and Error Recovery

1. Hard-Coded Task Completion Process

2. LLM Generated Plans:

    - CodeR (Chen et al. 2024)

3. Planning and Revisiting

4. Fix Based on Error Messages

    - Intercode (Yang et al. 2023)

#### Safety

    - Avoid causig harm by accident (e.g. The coding accidentally pushes to your main branch, or tell the model to make the test pass)
    - Intentionall misuse (e.g. hacking)
    - Mitigations

        - Sandboxing: limit the execution environment (e.g. Docker sandboxes)
        - Credentialling: The principle of least privilege. e.g. Github access tokens.
        - Post-hoc Auditing: Security Analyzer

#### Conclusion and Future Directions

##### Current Challenges
code LLMs, localization, planning and safety

#### Future

- Agentic Training Methods
- Human in the Loop
- Broader SW tasks than coding
