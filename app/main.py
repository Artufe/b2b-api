from fastapi import Depends, FastAPI

from app.users.db import database
from app.users.models import UserDB
from app.users.users import current_active_user, fastapi_users, jwt_authentication, cookie_authentication
from app.routes import (projects, queries, companies,
                        employees, image_templates, images,
                        queries_export, queries_new, stats)

app = FastAPI(
    title="B2B API",
    root_path="/api/v1",
    version="1"
)

# JWT token login router
app.include_router(
    fastapi_users.get_auth_router(jwt_authentication), prefix="/auth/jwt", tags=["auth"]
)
# Cookie based login route
# app.include_router(
#     fastapi_users.get_auth_router(cookie_authentication), prefix="/auth/cookie", tags=["auth"]
# )


app.include_router(
    fastapi_users.get_register_router(), prefix="/auth", tags=["auth"]
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(fastapi_users.get_users_router(), prefix="/users", tags=["users"])


app.include_router(image_templates.router)
app.include_router(images.router)
app.include_router(projects.router)
app.include_router(queries.router)
app.include_router(stats.router)
app.include_router(queries_export.router)
app.include_router(queries_new.router)
app.include_router(companies.router)
app.include_router(employees.router)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()
