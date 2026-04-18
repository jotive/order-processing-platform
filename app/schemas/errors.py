from pydantic import BaseModel, Field


class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs."""

    type: str = Field(description="URI reference identifying the problem type")
    title: str = Field(description="Short human-readable summary")
    status: int = Field(description="HTTP status code")
    detail: str | None = Field(default=None, description="Human-readable explanation")
    instance: str | None = Field(default=None, description="URI reference identifying the occurrence")


class ValidationErrorItem(BaseModel):
    field: str
    message: str


class ValidationProblem(ProblemDetail):
    errors: list[ValidationErrorItem] = Field(default_factory=list)
