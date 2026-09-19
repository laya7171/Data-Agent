from pydantic import BaseModel, Field
from typing import Annotated, Literal
from operator import add


class AgentState(BaseModel):
    user_question: str
    curated_question: str = ""
    prompt_query_context: str = ""
    generated_sql_query: str = ""
    is_safe: Literal["Yes", "No"] | None = None
    final_answer: str = ""
    comments: str = ""
    sql_query_execution_result: str = ""


class JudgeSchema(BaseModel):
    is_safe: Literal["Yes", "No"] | None = None

    comments: str = Field(
        ...,
        description="Explanation for why the SQL query was judged safe or unsafe."
    )
