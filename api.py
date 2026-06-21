import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

from steps import FewShot, UserPrompt, PseudoRAG, LLMClient, SecurityValidator, TerraformValidator
from pipeline import Pipeline

app = FastAPI(title="agentic-terraform API")

# Autorise le front-end (page HTML locale) à appeler cette API depuis le navigateur
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    success: bool
    terraform_code: str
    run_id: str
    message: str


def save_run(run_dir: Path, user_prompt: str, code: str, success: bool):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(user_prompt, encoding="utf-8")
    (run_dir / "output.tf").write_text(code, encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "prompt": user_prompt,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@app.post("/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest):
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = Path("runs") / f"{timestamp}_{run_id}"

    model_name = "gemini-2.5-flash"
    llm_client = genai.Client()

    steps = [
        FewShot(),
        UserPrompt(),
        PseudoRAG(),
        LLMClient(llm_client, model_name),
        SecurityValidator(),
        TerraformValidator(),
    ]

    pipeline = Pipeline(steps)

    try:
        result = pipeline.run(request.prompt)
        save_run(run_dir, request.prompt, last_code, success=True)
        return GenerateResponse(
            success=True,
            terraform_code=result,
            run_id=run_id,
            message="Code Terraform généré et validé avec succès.",
        )
    except SystemExit:
        save_run(run_dir, request.prompt, "", success=False)
        return GenerateResponse(
            success=False,
            terraform_code="",
            run_id=run_id,
            message="Échec après le nombre maximum de tentatives de correction.",
        )


@app.get("/health")
def health():
    return {"status": "ok"}
