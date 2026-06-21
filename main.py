# ==============================================================================
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# ==============================================================================

# import gemini
from google import genai
from pipeline import Pipeline
from steps import FewShot, LLMClient, PseudoRAG, SecurityValidator, TerraformValidator, UserPrompt

# Ref: https://docs.anthropic.com/en/docs/about-claude/models
# model_name = "claude-3- 5-haiku-latest"
# llm_client = anthropic.Anthropic()

model_name = "gemini-2.5-flash"
llm_client = genai.Client()   # lit GEMINI_API_KEY automatiquement depuis l'env

#user_prompt = "Deploy 3 VMs with at least 16 CPUs and 64GB across 3 AZs in Netherlands using Azure"
user_prompt = "Deploy a single VM on OVH Cloud with 4GB RAM in the Gravelines datacenter"

steps = [
    FewShot(),
    UserPrompt(),
    PseudoRAG(),
    LLMClient(llm_client, model_name),
    SecurityValidator(),
    TerraformValidator(),
]

pipeline = Pipeline(steps)
result = pipeline.run(user_prompt)
print(result)
