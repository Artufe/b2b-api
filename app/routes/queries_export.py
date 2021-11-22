import csv
import io
import gspread

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from app.dependencies import get_session
from app.users.users import current_active_user
from app.users.models import UserDB
from app.routes.companies import populate_emails

from app.models import (
    Query,
    Company,
    CompaniesMapsData,
)

router = APIRouter(
    prefix="/export",
    tags=["Query Export"],
    responses={404: {"description": "Not found"}},
)


@router.get("/{query_id}/csv")
async def export_csv(*,
                     session: Session = Depends(get_session),
                     user: UserDB = Depends(current_active_user),
                     query_id: int
                     ):
    query = session.query(Query).where(Query.user_id == user.id,
                                       Query.query_id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    companies = session.query(Company).where(Company.query_id == query_id).all()
    companies = populate_emails(companies)

    with io.StringIO() as buffer:
        writer = csv.writer(buffer)
        # Headers
        writer.writerow(["Company", "Website", "Employee name",
                         "Employee position", "Employee email",
                         "Contact Email", "Facebook", "Twitter",
                         "Youtube", "LinkedIn", "Instagram",
                         "Phone"])
        # Rows
        for c in companies:
            writer.writerow([c["name"], c["website"],
                             c["email"]["full_name"] if c.get("email") else "",
                             c["email"]["position"] if c.get("email") else "",
                             c["email"]["email"] if c.get("email") else "",
                             c["contact_email"], c["facebook"], c["twitter"],
                             c["youtube"], c["linkedin"], c["instagram"],
                             c["phone"]])

        headers = {
            'Content-Disposition': f'attachment; filename="B2B_export_{query.query_id}.csv"'
        }
        return StreamingResponse(iter([buffer.getvalue()]),
                                 media_type="text/csv",
                                 headers=headers)


@router.get("/{query_id}/sheet")
async def export_sheet(*,
                       session: Session = Depends(get_session),
                       user: UserDB = Depends(current_active_user),
                       query_id: int,
                       share_email: str = None
                       ):
    query = session.query(Query).where(Query.user_id == user.id,
                                       Query.query_id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    companies = session.query(Company).where(Company.query_id == query_id).all()

    # Connect to gsheets using a service account connection key file in home dir
    gc = gspread.service_account(filename="/run/secrets/service_account")

    # Open a sheet from a spreadsheet in one go
    if query.type == "standard":
        sh = gc.create(f"[B2B] {query.sector} in {query.location}")
    elif query.type == "from_csv":
        sh = gc.create(f"[B2B] CSV import #{query.id}")
    else:
        sh = gc.create(f"[B2B] Unknown query type (TODO) #{query.id}")

    # Share with the email if provided
    if share_email:
        sh.share(share_email, perm_type='user', role='writer')
    else:
        # Open the spreadsheet to anyone with URL otherwise
        sh.share('', perm_type='anyone', role='reader')

    # Setup the required worksheets, delete the default sheet,
    sum_sheet = sh.add_worksheet(title="Summary", rows="100", cols="20")
    com_sheet = sh.add_worksheet(title="Companies", rows="100", cols="20")
    emp_sheet = sh.add_worksheet(title="Employees", rows="100", cols="20")
    stat_sheet = sh.add_worksheet(title="Stats", rows="100", cols="20")
    sh.del_worksheet(sh.sheet1)

    # Populate the Companies sheet with headers and data
    com_rows = [["Company Name", "Website", "Employee Email",
                 "Employee Name", "Employees found", "Phone", "Full Address",
                 "Linkedin", "Twitter", "Facebook", "Instagram",
                 "Youtube", "Maps Rating", "Maps Reviews", "Maps Lat Long"]]

    all_employees = []
    for comp in companies:
        employees = comp.employees
        all_employees.extend(comp.employees)
        maps_data = session.query(CompaniesMapsData).where(CompaniesMapsData.company_id == comp.company_id).first()
        comp = populate_emails([comp])[0]

        if not comp.get("email"):
            comp["email"] = {"email": None, "full_name": None, "position": None}
        single_row = [comp["name"], comp["website"], comp["email"]["email"], comp["email"]["full_name"],
                      len(employees), comp["phone"], comp["full_address"],
                      comp["linkedin"], comp["twitter"], comp["facebook"],
                      comp["instagram"], comp["youtube"]]
        if maps_data:
            single_row.extend([maps_data.rating, maps_data.reviews,
                               f"{maps_data.lat},{maps_data.long}"])

        com_rows.append(single_row)

    com_sheet.update(f"A1:O{len(com_rows)}", com_rows)

    # Populate the employees table with headers and all employees of the companies in the query
    emp_rows = [["Company Name", "Full Name", "Position",
                 "Email", "Rank Score", "Linkedin URL"]]

    for emp in all_employees:
        emp_rows.append([emp.company.name, emp.full_name, emp.position, emp.email, emp.rank_score, emp.linkedin_url])

    emp_sheet.update(f"A1:F{len(emp_rows)}", emp_rows)

    # Populate the summary sheet with short format table of all emails found and their most vital info
    # Collect and calculate stats for the stat sheet
    emails_found = 0
    employees_with_emails = []
    for employee in all_employees:
        if employee.email and len(employee.email) > 2:
            emails_found += 1
            employees_with_emails.append(employee)

    if emails_found == 0:
        email_rate = 0
    else:
        email_rate = (emails_found / len(companies)) * 100

    time_taken = query.finished_at - query.started_at
    minutes_taken = time_taken.seconds // 60
    stat_sheet.update("A1:K8",
                      [[None, "Query Stats:", None],
                       [f"Launched", "Finished", "Time Taken"],
                       [f"{query.started_at.strftime('%d/%m/%Y, %H:%M:%S')}",
                        f"{query.finished_at.strftime('%d/%m/%Y, %H:%M:%S')}", f"{minutes_taken} minutes"],

                       ["Emails", "Email Rate", "Employees"],
                       [f"{emails_found}", f"{email_rate:.1f}%", f"{len(all_employees)}"],

                       [None, f"Companies", None],
                       [None, f"{len(companies)}", None]
                       ]
                      )

    # Short format table of results with emails
    sum_rows = [["Email", "First Name", "Last Name", "Position", "Company"]]

    for employee in employees_with_emails:
        sum_rows.append([employee.email, employee.first_name,
                         employee.last_name, employee.position,
                         employee.company.name])
    sum_sheet.update(f"A1:E{len(sum_rows)}", sum_rows)

    # Create a stats sheet, with some info on the rates and numbers

    return {"sheet_url": f"https://docs.google.com/spreadsheets/d/{sh.id}",
            "sheet_title": sh.title}
