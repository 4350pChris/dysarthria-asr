from typing import Annotated

from pydantic import BaseModel, StringConstraints


RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CategoryForm(BaseModel):
    name: RequiredText


class PhraseForm(BaseModel):
    text: RequiredText


class CreatePhraseForm(PhraseForm):
    category_id: int


class GrammarPatternForm(BaseModel):
    template: RequiredText


class GrammarValueForm(BaseModel):
    value: RequiredText
