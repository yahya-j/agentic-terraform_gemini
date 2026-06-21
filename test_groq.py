# test_groq.py
import groq

client = groq.Groq()
completion = client.chat.completions.create(
    max_tokens=200,
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "Write a minimal Terraform azurerm provider block."}]
)
print(completion.choices[0].message.content)
