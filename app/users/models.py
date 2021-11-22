import datetime
from typing import Optional
from fastapi_users import models

class User(models.BaseUser):
    first_name: str
    last_name: Optional[str]
    company_name: Optional[str]


class UserCreate(models.BaseUserCreate):
    first_name: str
    last_name: Optional[str]
    company_name: Optional[str]


class UserUpdate(models.BaseUserUpdate):
    first_name: Optional[str]
    last_name: Optional[str]
    company_name: Optional[str]


class UserDB(User, models.BaseUserDB):
    pass
