# ==============================================================================
# SPDX-License-Identifier: MPL-2.0
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
# ==============================================================================

import json
import os
import subprocess
import tempfile
import re

from google.genai import types
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Concat last messages from "assistant
def results(messages):
    result = []
    for message in messages[::-1]:
        if message["role"] != "assistant":
            break

        result.insert(0, message["content"])

    return "".join(result)

class SecurityValidator:
    # Chaque règle : (nom, regex, message d'erreur à renvoyer au LLM)
    RULES = [
        (
            "hardcoded_password",
            re.compile(r'admin_password\s*=\s*"[^"]+"'),
            'Do not hardcode "admin_password" in plain text. Remove the admin_password '
            'argument and instead use SSH key authentication via "admin_ssh_key" block, '
            'with disable_password_authentication = true.',
        ),
        (
            "password_auth_enabled",
            re.compile(r'disable_password_authentication\s*=\s*false'),
            'Set disable_password_authentication = true to enforce SSH key-only '
            'authentication instead of password authentication.',
        ),
        (
            "open_ssh_to_internet",
            re.compile(
                r'source_address_prefix\s*=\s*"\*"|source_address_prefix\s*=\s*"0\.0\.0\.0/0"'
            ),
            'Do not allow inbound traffic from "*" or "0.0.0.0/0". Restrict '
            'source_address_prefix to a specific known IP range.',
        ),
        (
            "hardcoded_secret_generic",
            re.compile(r'(secret|api_key|token)\s*=\s*"[^"]{8,}"', re.IGNORECASE),
            'Do not hardcode secrets, API keys, or tokens in plain text. Use a '
            'variable with sensitive = true, or reference a secrets manager.',
        ),
    ]

    def _extract_vm_blocks(self, code):
        """Extrait le contenu de chaque bloc azurerm_linux_virtual_machine
        en comptant les accolades, pour gérer correctement les blocs imbriqués."""
        blocks = []
        pattern = re.compile(r'resource\s+"azurerm_linux_virtual_machine"\s+"[^"]+"\s*\{')

        for match in pattern.finditer(code):
            start = match.end()  # juste après l'accolade ouvrante
            depth = 1
            i = start
            while i < len(code) and depth > 0:
                if code[i] == "{":
                    depth += 1
                elif code[i] == "}":
                      depth -= 1
                i += 1
            blocks.append(code[start:i - 1])  # contenu entre les accolades

        return blocks

    def _check_vm_has_auth(self, code):
        issues = []
        for block in self._extract_vm_blocks(code):
            if "admin_ssh_key" not in block and "admin_password" not in block:
                issues.append(
                    "A VM resource is missing authentication: add an "
                    '"admin_ssh_key" block (preferred) or "admin_password".'
                )
        return issues

    def get_messages(self, messages, _, meta):
        if not meta.get("AlreadyRun"):
            meta["AlreadyRun"] = True
            meta["RetryCount"] = 0

        iac_result = results(messages)

        if meta["RetryCount"] >= 5:
            print("[SecurityValidator] Nombre max de retries atteint. Abandon.")
            print("=== Dernier Code généré ===")
            print(iac_result)
            exit(1)

        
        violations = []
        for rule_name, pattern, fix_instruction in self.RULES:
            if pattern.search(iac_result):
                violations.append(f"- [{rule_name}] {fix_instruction}")

        # ↓↓↓ NOUVEAU ↓↓↓
        auth_issues = self._check_vm_has_auth(iac_result)
        violations.extend(f"- [missing_authentication] {issue}" for issue in auth_issues)
        # ↑↑↑ NOUVEAU ↑↑↑
        
        if not violations:
            print("[SecurityValidator] Aucun problème de sécurité détecté.")
            return messages, False, meta

        error = (
            "The generated Terraform code has security issues that must be fixed:\n"
            + "\n".join(violations)
        )
        print(f"[SecurityValidator] Problèmes détectés :\n{error}")
        meta["RetryCount"] += 1
        return messages + [{"role": "user", "content": error}], True, meta

class TerraformValidator:
    def get_messages(self, messages, _, meta):
        if not meta.get("AlreadyRun"):
            meta["AlreadyRun"] = True
            meta["RetryCount"] = 0

        print(f"[TerraformValidator] Tentative {meta['RetryCount'] + 1}/6")

        if meta["RetryCount"] >= 5:
            print("[TerraformValidator] Nombre max de retries atteint. Abandon.")
            print("=== Dernier Code généré ===")
            print(results(messages))
            exit(1)

        iac_result = results(messages)

        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "llm_iac.tf"), "w") as f:
                f.write(iac_result)

            init_handle = subprocess.run(
                ["terraform", "init"],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
            )

            if init_handle.returncode != 0:
                error = init_handle.stderr or init_handle.stdout
                print(f"[TerraformValidator] terraform init a échoué :\n{error}")
                meta["RetryCount"] += 1
                return messages + [{"role": "user", "content": error}], True, meta

            tf_handle = subprocess.run(
                ["terraform", "validate", "-json"],
                cwd=tmp_dir,
                capture_output=True,
                text=True,
            )
            tf_json = json.loads(tf_handle.stdout)

            if tf_json["valid"]:
                print("[TerraformValidator] Code Terraform valide !")
                return messages, False, meta

            error = tf_json["diagnostics"][0]["detail"]
            print(f"[TerraformValidator] terraform validate a échoué :\n{error}")
            meta["RetryCount"] += 1
            return messages + [{"role": "user", "content": error}], True, meta
            
class PseudoRAG:
    terraform_providers = {
        "azure": {
            "name": "azurerm",
            "keywords": ["azure", "microsoft azure"],
            "block": 'provider "azurerm" {\n  features {}\n}',
        },
        "aws": {
            "name": "aws",
            "keywords": ["aws", "amazon", "amazon web services"],
            "block": 'provider "aws" {\n  region = "eu-west-3"\n}',
        },
        "gcp": {
            "name": "google",
            "keywords": ["gcp", "google cloud", "google cloud platform"],
            "block": 'provider "google" {\n  project = "my-project-id"\n  region  = "europe-west1"\n}',
        },
        "ovh": {
            "name": "ovh",
            "keywords": ["ovh", "ovhcloud", "ovh cloud"],
            "block": (
                'terraform {\n'
                '  required_providers {\n'
                '    ovh = {\n'
                '      source  = "ovh/ovh"\n'
                '      version = "~> 0.34"\n'
                '    }\n'
                '  }\n'
                '}\n\n'
                'provider "ovh" {\n'
                '  endpoint = "ovh-eu"\n'
                '}'
            ),
        },
    }

    def __init__(self):
        # Compute text corpus
        self.corpus = {
            "data": [],
            "provider": [],
        }

        for _, provider in self.terraform_providers.items():
            for keyword in provider["keywords"]:
                self.corpus["data"].append(keyword.lower())
                self.corpus["provider"].append(key)

        self.vectorizer = TfidfVectorizer()
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus["data"])

    def get_messages(self, messages, user_prompt, meta):
        user_prompt_vector = self.vectorizer.transform([user_prompt])
        scores = cosine_similarity(user_prompt_vector, self.tfidf_matrix).tolist()[0]
        provider_key = self.corpus["provider"][scores.index(max(scores))]
        block = self.terraform_providers[provider_key]["block"]

        message = {"role": "assistant", "content": block}
        return messages + [message], False, meta


class FewShot:
    messages = [
        {
            "role": "user",
            "content": "Create an Ubuntu VM with 4 CPUs and 16GB RAM on AWS in the us-west-2 region.",
        },
        {
            "role": "assistant",
            "content": """
            resource "aws_instance" "vm" {
                ami           = "ami-0abcdef1234567890"
                instance_type = "t2.xlarge"
                availability_zone = "us-west-2a"
            }
            """,
        },
        {
            "role": "user",
            "content": "Deploy an S3 bucket with versioning enabled in the ap-southeast-1 region.",
        },
        {
            "role": "assistant",
            "content": """
            resource "aws_s3_bucket" "example" {
                bucket = "example-bucket"
                versioning {
                    enabled = true
                }
                region = "ap-southeast-1"
            }
            """,
        },
        {
            "role": "user",
            "content": "Create an Ubuntu VM on Azure with SSH key authentication, no password.",
        },
        {
            "role": "assistant",
            "content": (
                'resource "tls_private_key" "example" {\n'
                '  algorithm = "RSA"\n'
                '  rsa_bits  = 4096\n'
                '}\n\n'
                'resource "azurerm_linux_virtual_machine" "example" {\n'
                '  name                = "example-vm"\n'
                '  resource_group_name = azurerm_resource_group.example.name\n'
                '  location            = azurerm_resource_group.example.location\n'
                '  size                = "Standard_DS1_v2"\n'
                '  admin_username      = "adminuser"\n'
                '  network_interface_ids = [azurerm_network_interface.example.id]\n\n'
                '  disable_password_authentication = true\n\n'
                '  admin_ssh_key {\n'
                '    username   = "adminuser"\n'
                '    public_key = tls_private_key.example.public_key_openssh\n'
                '  }\n\n'
                '  os_disk {\n'
                '    caching              = "ReadWrite"\n'
                '    storage_account_type = "Standard_LRS"\n'
                '  }\n\n'
                '  source_image_reference {\n'
                '    publisher = "Canonical"\n'
                '    offer     = "0001-com-ubuntu-server-jammy"\n'
                '    sku       = "22_04-lts"\n'
                '    version   = "latest"\n'
                '  }\n'
                '}'
            ),
        },
    ]

    def get_messages(self, messages, _, meta):
        if meta.get("AlreadyRun"):
            return messages, False, meta

        meta["AlreadyRun"] = True

        return messages + self.messages, False, meta


class UserPrompt:
    def get_messages(self, messages, user_prompt, meta):
        if meta.get("AlreadyRun"):
            return messages, False, meta

        message = {"role": "user", "content": user_prompt}
        meta["AlreadyRun"] = True

        return messages + [message], False, meta


class LLMClient:
    def __init__(self, llm_client, model_name):
        self.llm_client = llm_client
        self.model_name = model_name

    def _to_gemini_contents(self, messages):
        """Convertit le format {'role': 'user'/'assistant', 'content': str}
        utilisé par le pipeline vers le format attendu par l'API Gemini."""
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
            )
        return contents

    def get_messages(self, messages, _, meta):
        system_instruction = (
            "You are a Terraform HCL code generator. Output ONLY raw Terraform HCL "
            "(.tf file syntax) — never Pulumi, never CloudFormation, never ARM "
            "templates, never any other IaC tool. Never include markdown formatting, "
            "explanations, prerequisites, deployment steps, or comments about your "
            "changes. Output must start directly with HCL code (e.g. 'resource' or "
            "'provider' block) and contain nothing else."
        )

        response = self.llm_client.models.generate_content(
            model=self.model_name,
            contents=self._to_gemini_contents(messages),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=1024,
            ),
        )

        return (
            messages + [{"role": "assistant", "content": response.text}],
            False,
            meta,
        )
