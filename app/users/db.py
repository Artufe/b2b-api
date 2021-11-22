import databases
import sqlalchemy
import os
from datetime import datetime

from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy import Column, String, DateTime

from app.users.models import UserDB
from app.dependencies import DB_URL

database = databases.Database(DB_URL)
Base: DeclarativeMeta = declarative_base()


class UserTable(Base, SQLAlchemyBaseUserTable):
    first_name = Column(String(50))
    last_name = Column(String(50))
    company_name = Column(String(50))
    created = Column(DateTime, default=datetime.utcnow)


engine = sqlalchemy.create_engine(DB_URL)
Base.metadata.create_all(engine)

users = UserTable.__table__


def get_user_db():
    yield SQLAlchemyUserDatabase(UserDB, database, users)
