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
    Company,
    CompanyRead,
    CompaniesMapsData,
    CompanyWithLocationDataRead,
    Query,
    Employee
)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


def populate_emails(companies):
    companies_with_emails = []
    last_employee_score = 0
    for company in companies:
        # Start by setting email var to none
        email = None
        for employee in company.employees:
            if employee.email and employee.rank_score > last_employee_score:
                # If email found, and is scored higher than last or default (0)
                # Update the email variable
                email = {"full_name": employee.full_name,
                         "position": employee.position,
                         "email": employee.email}
                last_employee_score = employee.rank_score

        # Convert the company to dict
        company = company.dict()
        if email:
            # If email found, add a key and value of it
            company["email"] = email

        companies_with_emails.append(company)
        # Reset the last score, for next loop
        last_employee_score = 0
    return companies_with_emails


@router.get("/all/{query_id}", response_model=List[CompanyRead])
async def get_all_companies(*,
                            session: Session = Depends(get_session),
                            user: UserDB = Depends(current_active_user),
                            query_id: int,
                            offset: int = 0,
                            limit: int = QueryFastapi(default=100, lte=100),
                            ):
    query = session.get(Query, query_id)
    if not query or query.user_id != user.id or not query.is_active:
        raise HTTPException(status_code=404, detail="Query not found")

    query = session.query(Company).where(Company.query_id == query_id)
    results = query.offset(offset).limit(limit).all()

    results_with_emails = populate_emails(results)
    return results_with_emails


@router.get("/{company_id}", response_model=CompanyWithLocationDataRead)
async def get_company(*,
                      session: Session = Depends(get_session),
                      user: UserDB = Depends(current_active_user),
                      include_loc_data: bool = True,
                      company_id: int
                      ):
    company = session.query(Company).where(
        Company.company_id == company_id).first()

    if not company\
            or company.query.user_id != user.id\
            or not company.query.is_active:
        raise HTTPException(status_code=404, detail="Company not found")

    company = populate_emails([company])[0]

    if include_loc_data:
        maps_data = session.query(CompaniesMapsData)\
            .where(CompaniesMapsData.company_id == company_id)\
            .first()
        company = {**company, **maps_data.dict()}

    return company
