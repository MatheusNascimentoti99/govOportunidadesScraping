"""
schemas.py – Schemas Pydantic para request/response da API.
"""
from pydantic import BaseModel, EmailStr, field_validator


class SubscribeRequest(BaseModel):
    email: EmailStr
    keywords: str

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("keywords não pode ser vazio.")
        return cleaned


class DedupCheckRequest(BaseModel):
    edital_url: str
    subscriber_email: str


class NotificationLogRequest(BaseModel):
    edital_url: str
    subscriber_email: str


class NotificationSendRequest(BaseModel):
    edital_url: str
    subscriber_email: EmailStr
    matched_keywords: list[str] = []
    summary: str = ""
    text: str = ""
