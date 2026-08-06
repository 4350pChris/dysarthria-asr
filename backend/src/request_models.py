from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints


RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CategoryRequest(BaseModel):
    name: RequiredText


class PhraseRequest(BaseModel):
    text: RequiredText


class CreatePhraseRequest(PhraseRequest):
    category_id: int


class GrammarPatternRequest(BaseModel):
    template: RequiredText


class GrammarValueRequest(BaseModel):
    value: RequiredText


class LabelUpdateRequest(BaseModel):
    transcript: str = ""
    status: Literal["draft", "labeled", "skipped"] = "draft"
    unsure: bool = False
    notes: str = ""
