# neurocore-skill-neuroweave

NeuroWeave knowledge graph memory skill for NeuroCore.

## Installation

```bash
pip install neurocore-skill-neuroweave
```

## Usage

Once installed, the `neuroweave` skill is automatically discovered by NeuroCore via entry points.

```yaml
# In your blueprint YAML
components:
  - name: memory
    type: neuroweave
    config:
      mode: context        # process | query | context
      llm_provider: mock   # mock | anthropic | openai
flow:
  type: sequential
  steps:
    - component: memory
```

## Modes

- **process**: Extract knowledge from a message and update the graph
- **query**: Query the knowledge graph for relevant context
- **context**: Both extract and query in one step (default)

## License

Apache-2.0
# neurocore-skill-neuroweave
