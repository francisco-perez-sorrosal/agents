# Lesson 8: Towards a unified framework of Neural and Symbolic Decision Making

## Speaker: Yuandong Tian

## Key Ideas and Takeaways

This course explores the integration of neural networks and symbolic methods to address limitations in decision-making tasks like reasoning and planning, where pure neural approaches, including state-of-the-art (SoTA) Large Language Models (LLMs), often struggle.

1. **Limitations of LLMs in Complex Planning:**
    - LLMs perform poorly in constrained, real-world tasks like travel and meeting planning due to their inability to handle combinatorial and multi-step constraints.
    - Examples include benchmarks like TravelPlanner (ICML’24) and NATURAL PLAN (arXiv’24) which reveal these gaps.

2. **Proposed Solutions for Enhanced Decision Making:**
    - **Scaling Law Approach:**
        - Larger models, more data, and increased computation, though costly, show limited improvement in reasoning tasks.
    - **Hybrid Systems:**
        - Combining neural models with symbolic tools like combinatorial solvers. Example:
        - Mixed Integer Linear Programming (MILP) for travel planning converts user instructions into symbolic constraints, achieving optimal solutions.
    - **Emergent Symbolic Structures:**
        - Deep models show potential to implicitly converge to symbolic reasoning structures (e.g., Fourier features for modular addition).
        - Raises questions about whether neural networks perform genuine reasoning or rely on pattern retrieval.

3. **Techniques for Enhanced Planning and Optimization:**
    - **Search-Augmented Models:**
        - Enhance neural decision-making by integrating search algorithms (e.g., A*) as token prediction tasks.
        - Example: Searchformer, combining search dynamics with Transformer-based models, outperforms purely solution-driven systems.
    - **Differentiable Optimization:**
        - Techniques like SurCo use surrogate models to solve combinatorial optimization problems in latent spaces efficiently, with applications in photonics design and energy grids.
    - **Composing Global Optimizers:**
        - Leveraging algebraic structures in neural networks (e.g., Ring Homomorphisms) to build partial and global optimizers for complex nonlinear objectives.

4. **Future Directions and Implications:**
    - Investigating whether neural networks learn symbolic representations or efficient algebraic solutions.
    - The possibility of gradient descent becoming obsolete in favor of advanced algebraic optimization methods.

This framework highlights the necessity of hybrid systems and interdisciplinary methods to overcome LLMs’ limitations, paving the way for more robust and efficient decision-making agents.

# One paragraph summary:

Lesson 8 explores the integration of neural networks and symbolic methods to address the limitations of Large Language Models (LLMs) in complex decision-making tasks like reasoning and planning, which require handling constraints and multi-step processes. Yuandong Tian outlines key challenges, such as LLMs’ struggles with real-world planning benchmarks like TravelPlanner, and proposes solutions like scaling laws, hybrid systems that integrate neural models with symbolic solvers (e.g., Mixed Integer Linear Programming), and emergent symbolic structures within deep models. Techniques like search-augmented models, differentiable optimization, and algebraic structures enhance planning efficiency and problem-solving. The lesson emphasizes hybrid frameworks and interdisciplinary approaches to create more robust AI agents and suggests a future where neural networks may evolve into advanced symbolic reasoning systems, potentially replacing gradient descent.