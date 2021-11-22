from typing import List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query as QueryFastapi
)
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.models import (
    Employee,
    EmployeeRead,
    Company,
    Query
)

router = APIRouter(
    prefix="/employees",
    tags=["Company Employees"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.get("/company/{company_id}", response_model=List[EmployeeRead])
async def get_all_employees(*,
                            session: Session = Depends(get_session),
                            user: UserDB = Depends(current_active_user),
                            company_id: int,
                            offset: int = 0,
                            limit: int = QueryFastapi(default=100, lte=100)
                            ):
    company = session.get(Company, company_id)
    if not company \
            or company.query.user_id != user.id \
            or not company.query.is_active:
        raise HTTPException(status_code=404, detail="The company requested was not found or you are not authorized to view it.")

    query = session.query(Employee).where(Employee.company_id == company_id)
    results = query.offset(offset).limit(limit).all()
    return results


@router.get("/query/{query_id}", response_model=List[EmployeeRead])
async def get_all_employees_from_query(*,
                                       session: Session = Depends(get_session),
                                       user: UserDB = Depends(current_active_user),
                                       query_id: int,
                                       offset: int = 0,
                                       limit: int = QueryFastapi(default=100, lte=100)
                                       ):
    query = session.get(Query, query_id)
    if not query \
            or query.user_id != user.id \
            or not query.is_active:
        raise HTTPException(status_code=404, detail="The query requested was not found or you are not authorized to view it.")

    employee_query = session.query(Employee).join(Company).where(Company.query_id == query_id)
    results = employee_query.offset(offset).limit(limit).all()
    return results


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(*,
                       session: Session = Depends(get_session),
                       user: UserDB = Depends(current_active_user),
                       employee_id: int,
                       ):
    employee = session.get(Employee).where(Employee.employee_id == employee_id)
    if not employee \
            or employee.company.query.user_id != user.id \
            or not employee.company.query.is_active:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
