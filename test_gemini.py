import os
from google import genai
from google.genai import types

# Vérification que la clé est bien présente avant d'appeler l'API
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY n'est pas défini. Faites: export GEMINI_API_KEY=AIza...")

client = genai.Client()  # lit GEMINI_API_KEY automatiquement depuis l'env

# --- Test 1 : appel le plus simple possible (une string) ---
print("=== Test 1 : appel simple ===")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Write a minimal Terraform azurerm provider block.",
)
print(response.text)

# --- Test 2 : appel avec une liste de messages façon conversation ---
# C'est ce format qu'on va devoir utiliser dans le pipeline, car FewShot/UserPrompt
# construisent une liste de tours de conversation, pas une simple string.
print("\n=== Test 2 : appel avec historique de conversation ===")
contents = [
    types.Content(role="user", parts=[types.Part.from_text(text="Create an Ubuntu VM with 4 CPUs on AWS.")]),
    types.Content(role="model", parts=[types.Part.from_text(text='resource "aws_instance" "vm" { ... }')]),
    types.Content(role="user", parts=[types.Part.from_text(text="Now do the same for Azure.")]),
]
response2 = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=contents,
)
print(response2.text)

print("\n=== Métadonnées utiles ===")
print("Tokens utilisés :", response2.usage_metadata)
