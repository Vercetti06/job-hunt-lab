from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel

from app import storage
from app.agents import profile_interview
from app.models import Profile

router = APIRouter(prefix="/api/profile", tags=["profile"])


class InterviewTurnRequest(BaseModel):
    message: str


@router.get("")
def get_profile() -> Profile:
    return storage.load_profile()


@router.put("")
def put_profile(profile: Profile) -> Profile:
    profile.is_complete = True
    storage.save_profile(profile)
    return profile


@router.get("/interview/history")
def get_history() -> List[Dict[str, Any]]:
    return storage.load_interview_history()


@router.post("/interview/reset")
def reset_interview() -> Dict[str, str]:
    storage.reset_interview_history()
    return {"status": "reset"}


@router.post("/interview/turn")
def interview_turn(body: InterviewTurnRequest) -> Dict[str, Any]:
    history = storage.load_interview_history()
    if body.message.strip():
        history.append({"role": "user", "content": body.message})

    result = profile_interview.step(history)

    if result["done"]:
        profile: Profile = result["profile"]
        storage.save_profile(profile)
        history.append({"role": "assistant", "content": "Great — I've got what I need. Your profile is saved."})
        storage.save_interview_history(history)
        return {"done": True, "profile": profile.model_dump()}

    question = result["question"]
    history.append({"role": "assistant", "content": question})
    storage.save_interview_history(history)
    return {"done": False, "question": question}
