# Agent-Practise

A local AI agent practice project for generating Mermaid flowcharts from natural language.
##The first four version just build up a simple structure and can only handle with a single-line Flow
1. version 1: A simple and initial Code for Flowchart agent
2. version 2: It cannot recognize '起点是' as start and '因此' as a result
3. version 3: The existed problem was solved but The normalize_roles_function should be improved in order to recognize different input styles from users
4. version 4: It could be used for generate a simple Mermaid code and a Processor is added in the code; However, this version can only handle with a single-line Flow and generate"A → B → C"

## Current Pipeline
### May 8th 2026
The current version implements a multi-stage flowchart generation pipeline:

1. Input Reader
2. Research Agent
3. Decomposition Agent
4. Flow Segmenter
5. Router
6. Linear / Branch Extractor
7. Repair and Validation
8. Mermaid Generator
9. Output Files

## Verified Test Cases

The current main branch has passed four manual test cases:

- TEST1: Login and permission-checking flow
- TEST2: File upload and parsing flow
- TEST3: Project approval flow
- TEST4: Agent flowchart generation flow