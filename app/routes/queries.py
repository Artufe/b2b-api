from typing import List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query as QueryFastapi
)
from typing import Optional
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB

from app.models import (
    Query,
    QueryRead,
)

router = APIRouter(
    prefix="/queries",
    tags=["Queries"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[QueryRead])
async def get_all_queries(*,
                          session: Session = Depends(get_session),
                          user: UserDB = Depends(current_active_user),
                          project_id: Optional[int] = None,
                          offset: int = 0,
                          limit: int = QueryFastapi(default=100, lte=100)
                          ):
    if project_id:
        query = session.query(Query).where(Query.user_id == user.id,
                                           Query.project_id == project_id,
                                           Query.is_active == True)
        results = query.offset(offset).limit(limit).all()
    else:
        query = session.query(Query).where(Query.user_id == user.id,
                                           Query.is_active == True)
        results = query.offset(offset).limit(limit).all()

    if not results:
        return []
    return results


@router.get("/{query_id}", response_model=QueryRead)
async def get_query(*,
                    session: Session = Depends(get_session),
                    user: UserDB = Depends(current_active_user),
                    query_id: int
                    ):
    query = session.query(Query).where(Query.user_id == user.id,
                                       Query.query_id == query_id,
                                       Query.is_active == True).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    return query


@router.delete("/{query_id}")
async def delete_query(*,
                       session: Session = Depends(get_session),
                       user: UserDB = Depends(current_active_user),
                       query_id: int
                       ):
    query = session.query(Query).where(Query.user_id == user.id,
                                       Query.query_id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    query.is_active = False
    try:
        session.commit()
    except IntegrityError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error.__cause__).replace("\n", " ").strip()
        ) from error
    return {"ok": True}

