from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
)
from sqlmodel import Session
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.models import (
    ProjectStats,
    QueryStats,
    Employee,
    Query
)

router = APIRouter(
    prefix="/stats",
    tags=["Statistics"],
    # dependencies=[Depends(current_active_user)],
    responses={404: {"description": "Not found"}},
)


@router.get("/query", response_model=QueryStats)
async def get_query_stats(*,
                          session: Session = Depends(get_session),
                          user: UserDB = Depends(current_active_user),
                          query_id: Optional[int] = None
                          ):
    query = session.query(Query).where(Query.query_id == query_id, Query.user_id == user.id).first()
    if not query:
        # To keep it consistent with the project stats behaviour
        return {
            "total_companies": 0,
            "total_employees": 0,
            "total_emails": 0,
            "minutes_taken": 0
        }

    total_companies_sql = "SELECT COUNT(*) FROM companies c " \
                          f"WHERE c.query_id = {query_id} "

    total_employees_sql = "SELECT COUNT(*) FROM employees e " \
                          "NATURAL JOIN companies c " \
                          f"WHERE c.query_id = {query_id} "

    total_emails_sql = "SELECT COUNT(*) FROM employees e " \
                       "NATURAL JOIN companies c " \
                       f"WHERE c.query_id = {query_id} " \
                       "AND e.email != '' "

    companies_by_size_sql = "SELECT count(*), company_id FROM employees e " \
                            "NATURAL JOIN companies c " \
                            f"WHERE c.query_id={query_id} " \
                            "GROUP BY e.company_id"

    # First fetch all of the one col one row sql results
    stats_prep = {
        "total_companies": total_companies_sql,
        "total_employees": total_employees_sql,
        "total_emails": total_emails_sql,
    }
    stats = {k: session.exec(v).first()[0] for k, v in stats_prep.items()}

    # Now fetch the multi column responses
    stats["companies_by_size"] = session.exec(companies_by_size_sql).all()

    # 1. Loop over all of the companies_by_size results
    # 2. Keep track of company size (number of employees) with Counter
    # 3. See if company has email found, keep track of emails found
    #    based on the company size
    # 4. Store results in a list of tuples
    size_tracker = []
    for x in range(1, max([x[0] for x in stats["companies_by_size"]]) + 1):
        emails_found = 0
        companies_found = 0
        for employee_number, company_id in stats["companies_by_size"]:
            if employee_number == x:
                companies_found += 1
                if session.query(Employee).where(Employee.email != '', Employee.company_id == company_id).first():
                    emails_found += 1
        size_tracker.append((x, companies_found, emails_found))

    del stats["companies_by_size"]
    stats["companies_by_size_labels"] = [x[0] for x in size_tracker]
    stats["companies_by_size_data"] = [x[1] for x in size_tracker]
    stats["emails_found_by_size_data"] = [x[2] for x in size_tracker]

    time_taken = query.finished_at - query.started_at
    minutes_taken = time_taken.seconds // 60
    stats["minutes_taken"] = minutes_taken

    return stats


@router.get("/project", response_model=ProjectStats)
async def get_project_stats(*,
                            session: Session = Depends(get_session),
                            user: UserDB = Depends(current_active_user),
                            project_id: Optional[int] = None
                            ):
    queries_in_progress_sql = f"SELECT COUNT(*) FROM queries q " \
                              f"WHERE is_active AND user_id='{user.id}' " \
                              f"AND finished_at IS NULL "

    total_companies_sql = "SELECT COUNT(*) FROM companies AS c " \
                          "JOIN queries AS q ON c.query_id = q.query_id " \
                          f"WHERE q.user_id = '{user.id}' "

    total_employees_sql = "SELECT COUNT(*) FROM employees e " \
                          "NATURAL JOIN companies c " \
                          "NATURAL JOIN queries q  " \
                          f"WHERE q.user_id = '{user.id}' "

    total_emails_sql = "SELECT COUNT(*) FROM employees e " \
                       "NATURAL JOIN companies c " \
                       "NATURAL JOIN queries q  " \
                       f"WHERE q.user_id = '{user.id}' " \
                       "AND e.email != '' "

    stats = {
        "queries_in_progress": queries_in_progress_sql,
        "total_companies": total_companies_sql,
        "total_employees": total_employees_sql,
        "total_emails": total_emails_sql
    }

    if project_id:
        stats = {k: v + f"AND q.project_id={project_id}" for k, v in stats.items()}

    return {k: session.exec(v).first()[0] for k, v in stats.items()}
