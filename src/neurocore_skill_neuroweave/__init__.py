"""NeuroWeave skill for NeuroCore.

Bridges NeuroWeave's knowledge graph memory into NeuroCore's
skill system. Registers via the `neurocore_ai.skills` entry point.

Usage in a blueprint:
    components:
      - name: memory
        type: neuroweave
        config:
          mode: context          # process | query | context
          llm_provider: mock     # mock | anthropic | openai
          llm_model: "claude-haiku-4-5-20251001"
    flow:
      type: sequential
      steps:
        - component: memory
"""

from neurocore_skill_neuroweave.skill import NeuroWeaveSkill

__version__ = "0.1.1"
__all__ = ["NeuroWeaveSkill"]
