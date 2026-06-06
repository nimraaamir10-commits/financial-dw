"""
UC2 — Data Source endpoints
  Q3: GET /sources         → list (summary)
  Q4: GET /sources/{id}    → full detail
"""

from fastapi import APIRouter, HTTPException, Depends

from db.client import get_db
from db.repository import DataSourceRepository

router = APIRouter(prefix="/sources", tags=["Data Sources"])


def get_repo(db=Depends(get_db)):
    return DataSourceRepository(db)


@router.get("/", summary="[Q3] List all data sources")
async def list_sources(repo: DataSourceRepository = Depends(get_repo)):
    """Returns identification data for every registered financial data provider."""
    sources = await repo.list_all()
    return {"count": len(sources), "sources": [s.model_dump() for s in sources]}


@router.get("/{source_id}", summary="[Q4] Get full data source detail")
async def get_source(source_id: str, repo: DataSourceRepository = Depends(get_repo)):
    """Returns full metadata for a specific data provider."""
    doc = await repo.get_by_id(source_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
    return doc
