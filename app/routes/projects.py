from typing import List
import datetime
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query
)
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.models import (
    Project,
    ProjectRead,
)

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.post("/new")
async def create_project(*,
                         session: Session = Depends(get_session),
                         user: UserDB = Depends(current_active_user),
                         project_name: str
                         ):
    session.add(Project(name=project_name, user_id=user.id))

    try:
        session.commit()
    except IntegrityError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error.__cause__).replace("\n", " ").strip()
        ) from error
    return {"ok": True}

@router.get("/", response_model=List[ProjectRead])
async def get_all_projects(*,
                           session: Session = Depends(get_session),
                           user: UserDB = Depends(current_active_user),
                           offset: int = 0,
                           limit: int = Query(default=100, lte=100)
                           ):
    query = session.query(Project).where(Project.user_id == user.id, Project.is_active == True)
    results = query.offset(offset).limit(limit).all()
    return results


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(*,
                      session: Session = Depends(get_session),
                      user: UserDB = Depends(current_active_user),
                      project_id: int
                      ):
    project = session.query(Project).where(Project.user_id == user.id,
                                           Project.project_id == project_id,
                                           Project.is_active == True).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(*,
                         session: Session = Depends(get_session),
                         user: UserDB = Depends(current_active_user),
                         project_id: int
                         ):
    project = session.query(Project).where(Project.user_id == user.id,
                                           Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.is_active = False
    project.updated_at = datetime.datetime.utcnow()
    try:
        session.commit()
    except IntegrityError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error.__cause__).replace("\n", " ").strip()
        ) from error
    return {"ok": True}
