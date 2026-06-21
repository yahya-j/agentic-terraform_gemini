<!--
SPDX-License-Identifier: MPL-2.0
-->

# Agentic Terraform

This repository implements an intelligent workflow that enhances LLM-generated Infrastructure-as-Code (IaC) using:

- [Few-shot prompting](https://en.wikipedia.org/wiki/Prompt_engineering#In-context_learning)
- [Pseudo-RAG](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)
- Automated validation and retry mechanisms

## Components

### 1. Pipeline (`pipeline.py`)
Orchestrates the workflow by integrating all steps below.

### 2. Steps (`steps.py`)
Contains the core processing modules:

- **FewShot**: Uses curated examples to guide the LLM in generating accurate IaC
- **PseudoRAG**: Generates appropriate `Terraform` provider clauses using [tf-idf](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) classification
- **TerraformValidator**: Validates generated IaC and implements retry logic for incomplete/invalid outputs

## Getting Started

### Prerequisites
- Python 3.12 or newer
- Terraform CLI (must be in system PATH)

### Installation

1. Clone the repository:
   ```shell
   git clone https://github.com/yahya-j/agentic-terraform_groq.git
   cd agentic-terraform_groq
   ```

2. Set up the environment:
    ```shell
   # Using micromamba (recommended)
   micromamba create -f environment.yml
   micromamba activate agentic-terraform_groq

   # Install development dependencies
   pipenv install --dev
   
   # Using python venv
   python3 -m venv venv
   source venv/bin/activate
   which python     
   pip install --upgrade pip
   pip install groq scikit-learn

   ```

### Usage

1. Set your API key:
   ```shell
   export GROQ_API_KEY=gsk_................
   echo 'export GROQ_API_KEY=gsk_.....' >> ~/.bashrc
   pip install --upgrade pip
   pip install groq scikit-learn
   ```

2. Run the example:
   ```shell
   pipenv shell
   python ./main.py
   ```

## Example Implementation

```python
import groq
from pipeline import Pipeline
from steps import FewShot, LLMClient, PseudoRAG, TerraformValidator, UserPrompt

def main():
    # Configure the pipeline
    model_name = "llama-3.3-70b-versatile"
    llm_client = groq.Groq()   # lit GROQ_API_KEY depuis l'env automatiquement

    # Define infrastructure requirements
    prompt = """
    Deploy 3 VMs with:
    - 16+ CPUs each
    - 64GB RAM each
    - Distributed across 3 availability zones
    - Located in the Netherlands
    - Using Azure as provider
    """

    # Set up pipeline steps
    steps = [
        FewShot(),
        UserPrompt(),
        PseudoRAG(),
        LLMClient(llm_client, model_name),
        TerraformValidator(),
    ]

    # Execute and get results
    pipeline = Pipeline(steps)
    result = pipeline.run(prompt)
    print(result)

if __name__ == "__main__":
    main()
```

## Development

### Validation Process
The retry mechanism utilises `terraform validate -json` to verify IaC syntax and structure.

### Contributing
1. Fork the repository
2. Install pre-commit hooks: `pre-commit install`
3. Create a feature branch
4. Submit a pull request with detailed description

## Licence

Licensed under the [Mozilla Public License 2.0 (MPL-2.0)](https://www.mozilla.org/en-US/MPL/2.0/).
See [LICENCE](LICENSE.md) for details and [legal TL;DR](https://www.tldrlegal.com/license/mozilla-public-license-2-0-mpl-2).
