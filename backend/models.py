from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class GenerateTasksResponse(BaseModel):
    """Kết quả sinh đề viết IELTS gồm Task 1 và Task 2."""

    task1: str = Field(..., description="Đề bài IELTS Writing Task 1")
    task2: str = Field(..., description="Đề bài IELTS Writing Task 2")
    task1_chart_data: Optional[str] = Field(None, description="Dữ liệu biểu đồ/bảng cho Task 1 (JSON hoặc text format)")
    task1_chart_image: Optional[str] = Field(None, description="Hình ảnh biểu đồ cho Task 1 (base64 encoded PNG)")


class GradeRequest(BaseModel):
    """Yêu cầu chấm bài: gồm đề, bài viết và loại task."""

    prompt: str
    essay: str
    task_type: Literal["task1", "task2"] = "task2"


class GradeBatchRequest(BaseModel):
    """Yêu cầu chấm cả Task 1 và Task 2 trong một lần gửi."""

    task1_prompt: str
    task1_essay: str
    task2_prompt: str
    task2_essay: str


class CriterionScore(BaseModel):
    """Điểm chi tiết theo band descriptor."""

    name: str
    band: float
    comment: str


class GradeResponse(BaseModel):
    """Phản hồi chấm bài gồm điểm, nhận xét và gợi ý cải thiện."""

    overall_band: float
    criteria: List[CriterionScore]
    feedback: str
    suggestions: str
    improved_version: Optional[str] = None


class GradeBatchResponse(BaseModel):
    """Kết quả chấm batch cho Task 1 và Task 2."""

    task1: GradeResponse
    task2: GradeResponse
