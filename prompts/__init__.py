"""P3 Agent Engine - Prompt Templates Package.

Exports S0 (Topology Discovery) and S1 (Procedure Generation) prompt templates
used for LLM-driven test procedure orchestration.
"""

from prompts.s0_prompt import (
    S0_SYSTEM_PROMPT,
    S0_USER_PROMPT_TEMPLATE,
)

from prompts.s1_prompt import (
    S1_SYSTEM_PROMPT,
    S1_USER_PROMPT_TEMPLATE,
)

__all__ = [
    "S0_SYSTEM_PROMPT",
    "S0_USER_PROMPT_TEMPLATE",
    "S1_SYSTEM_PROMPT",
    "S1_USER_PROMPT_TEMPLATE",
]
