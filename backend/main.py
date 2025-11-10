from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from .config import get_settings
from .gemini_client import GeminiClient
from .models import GenerateTasksResponse, GradeRequest, GradeResponse, GradeBatchRequest, GradeBatchResponse

app = FastAPI(title="IELTS Writing Assistant")

# CORS cho frontend tĩnh
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Endpoint tương thích cũ: chuyển hướng sang API mới
@app.get("/api/generate_task")
def legacy_generate_task_redirect():
    return RedirectResponse(url="/api/generate_tasks", status_code=307)


@app.get("/api/generate_tasks", response_model=GenerateTasksResponse)
def generate_tasks() -> GenerateTasksResponse:
    try:
        settings = get_settings()
        client = GeminiClient(settings.google_api_key, settings.gemini_model)
        return client.generate_writing_tasks()
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/grade", response_model=GradeResponse)
def grade(payload: GradeRequest) -> GradeResponse:
    if not payload.prompt or not payload.essay:
        raise HTTPException(status_code=400, detail="Thiếu prompt hoặc essay")
    try:
        settings = get_settings()
        client = GeminiClient(settings.google_api_key, settings.gemini_model)
        return client.grade_essay(payload.prompt, payload.essay, task_type=payload.task_type)
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/grade_batch", response_model=GradeBatchResponse)
def grade_batch(payload: GradeBatchRequest) -> GradeBatchResponse:
    if not all([payload.task1_prompt, payload.task1_essay, payload.task2_prompt, payload.task2_essay]):
        raise HTTPException(status_code=400, detail="Thiếu dữ liệu task1/task2")
    try:
        settings = get_settings()
        client = GeminiClient(settings.google_api_key, settings.gemini_model)
        result = client.grade_batch(
            task1_prompt=payload.task1_prompt,
            task1_essay=payload.task1_essay,
            task2_prompt=payload.task2_prompt,
            task2_essay=payload.task2_essay,
        )
        return GradeBatchResponse(task1=result["task1"], task2=result["task2"])
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc
