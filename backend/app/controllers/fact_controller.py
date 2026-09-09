from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from app.models.fact import FactOut
from app.dependencies import get_fact_repository, get_retrieval_service

router = APIRouter()


@router.get("/users/{user_id}/facts", response_model=list[FactOut])
def get_facts(user_id: UUID, repo=Depends(get_fact_repository)):
    return repo.find_by_user_id(user_id)


@router.get("/users/{user_id}/facts/search")
def search_facts(user_id: UUID, q: str, retrieval=Depends(get_retrieval_service)):
    results = retrieval.retrieve(user_id, q)
    return {"results": results}


@router.delete("/facts/{fact_id}", status_code=204)
def delete_fact(fact_id: UUID, repo=Depends(get_fact_repository)):
    repo.delete(fact_id)
    return None
