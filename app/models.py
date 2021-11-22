from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel, Column, JSON, LargeBinary
import uuid
from app.dependencies import engine


# Projects
class ProjectBase(SQLModel):
    __tablename__ = "projects"
    name: str
    is_active: bool = True


class ProjectCreate(ProjectBase):
    pass


class Project(ProjectBase, table=True):
    project_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    user_id: Optional[uuid.UUID]

    queries: List["Query"] = Relationship(back_populates="project")

    created_at: Optional[datetime] = datetime.now()
    updated_at: Optional[datetime] = datetime.now()


class ProjectRead(ProjectBase):
    project_id: int
    created_at: datetime
    updated_at: datetime


class ProjectStats(SQLModel):
    total_companies: int
    total_employees: int
    total_emails: int
    queries_in_progress: int


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


# Queries
class QueryBase(SQLModel):
    __tablename__ = "queries"
    sector: Optional[str] = None
    location: Optional[str] = None
    type: str
    maps_results: Optional[int]
    search_results: Optional[int]


class Query(QueryBase, table=True):
    query_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    user_id: Optional[uuid.UUID] = Field(default=None)
    is_active: bool = True

    project_id: Optional[int] = Field(default=None, foreign_key="projects.project_id")
    project: Project = Relationship(back_populates="queries")

    companies: List["Company"] = Relationship(back_populates="query")

    started_at: Optional[datetime] = datetime.utcnow()
    finished_at: Optional[datetime]


class QueryRead(QueryBase):
    query_id: int
    project_id: int
    started_at: datetime
    finished_at: Optional[datetime]


class QueryStats(SQLModel):
    total_companies: int
    total_employees: int
    total_emails: int
    minutes_taken: int
    companies_by_size_labels: List[str]
    companies_by_size_data: List[int]
    emails_found_by_size_data: List[int]


# Companies
class CompanyBase(SQLModel):
    __tablename__ = "companies"
    name: str
    website: Optional[str]
    phone: Optional[str]
    full_address: Optional[str]
    borough: Optional[str]
    line1: Optional[str]
    city: Optional[str]
    zip: Optional[str]
    region: Optional[str]
    country_code: Optional[str]
    contact_email: Optional[str]
    other_emails: Optional[str]
    linkedin: Optional[str]
    twitter: Optional[str]
    facebook: Optional[str]
    instagram: Optional[str]
    youtube: Optional[str]


class Company(CompanyBase, table=True):
    company_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    query_id: int = Field(default=None, foreign_key="queries.query_id")
    query: Query = Relationship(back_populates="companies")

    employees: List["Employee"] = Relationship(back_populates="company")
    maps_data: Optional["CompaniesMapsData"] = Relationship(back_populates="company")


class CompanyWithLocationDataRead(CompanyBase):
    search_position: int
    lat: int
    long: int
    rating: int
    reviews: int
    type: str
    thumbnail: Optional[str]
    email: Optional[dict]
    company_id: int
    query_id: int
    maps_data_id: int


class CompanyRead(CompanyBase):
    company_id: int
    query_id: int
    email: Optional[dict]


# Employees
class EmployeeBase(SQLModel):
    __tablename__ = "employees"
    full_name: str
    first_name: str
    last_name: Optional[str]
    position: str
    extracted_company: str
    email: Optional[str]
    rank_score: int
    search_title: str
    pre_snippet: Optional[str]
    linkedin_url: str


class Employee(EmployeeBase, table=True):
    employee_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    company_id: int = Field(default=None, foreign_key="companies.company_id")
    company: Company = Relationship(back_populates="employees")


class EmployeeRead(EmployeeBase):
    employee_id: int
    company_id: int


# Company Maps data (google maps)
class CompaniesMapsDataBase(SQLModel):
    __tablename__ = "companies_maps_data"
    search_position: int
    lat: float
    long: float
    rating: int = Field(default=0)
    reviews: int = Field(default=0)
    type: str
    thumbnail: Optional[str]


class CompaniesMapsData(CompaniesMapsDataBase, table=True):
    maps_data_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    company_id: int = Field(default=None, foreign_key="companies.company_id")
    company: Company = Relationship(back_populates="maps_data")


class CompaniesMapsDataRead(CompaniesMapsDataBase):
    maps_data_id: int
    company_id: int


# Image templates
class ImageTemplateBase(SQLModel):
    __tablename__ = "image_templates"
    top: int
    left: int
    font_weight: int
    font_style: str
    font_size: int
    font_family: str
    font_underline: bool
    font_color: Optional[str] = "#000000"
    rotation: Optional[int] = 0
    box_width: int
    box_height: Optional[int] = 200
    content: str


class ImageTemplateCreate(ImageTemplateBase):
    pass


class ImageTemplate(ImageTemplateBase, table=True):
    image_template_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    user_id: uuid.UUID
    created_at: Optional[datetime] = datetime.utcnow()
    updated_at: Optional[datetime] = datetime.utcnow()
    base_image: Optional[bytes] = Field(sa_column=Column(LargeBinary()))
    base_image_format: Optional[str] = Field(default=None)


class ImageTemplateRead(ImageTemplateBase):
    image_template_id: int
    created_at: datetime
    updated_at: datetime
    images_generated: Optional[int] = 0
    thumbnail: Optional[str]
    thumbnail_id: Optional[int]


class ImageTemplateUpdate(SQLModel):
    __tablename__ = "image_templates"
    top: Optional[int]
    left: Optional[int]
    font_weight: Optional[int]
    font_style: Optional[str]
    font_size: Optional[int]
    font_family: Optional[str]
    font_underline: Optional[bool]
    font_color: Optional[str]
    rotation: Optional[int]
    box_width: Optional[int]
    box_height: Optional[int]
    content: Optional[str]


# Images
class ImageBase(SQLModel):
    __tablename__ = "images"
    image: bytes = Field(sa_column=Column(LargeBinary()))
    thumbnail: bytes = Field(sa_column=Column(LargeBinary()))
    image_format: str = Field(default=None)
    preview: bool
    parameters: Optional[Dict[Any, Any]] = Field(
        index=False,
        sa_column=Column(JSON),
        default=None,
        nullable=True
    )


class Image(ImageBase, table=True):
    image_id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    template_id: Optional[int] = Field(default=None)
    user_id: uuid.UUID

    created_at: Optional[datetime] = datetime.utcnow()


class ImageRead(SQLModel):
    image: str
    thumbnail: str
    image_format: str
    preview: bool
    image_id: int
    template_id: int
    created_at: datetime


class ImageGenerate(BaseModel):
    image_template_id: int = Field(title="ID of the template to use for generating the image")


class SingleImageGenerate(ImageGenerate):
    """A model for submitting a one-off image to be generated from a template"""

    fname: Optional[str] = Field(
        None, title="Substitutes all occurrences of {FNAME} within the content of the template with this value.",
        max_length=50
    )
    lname: Optional[str] = Field(
        None, title="Substitutes all occurrences of {LNAME} within the content of the template with this value.",
        max_length=50
    )
    full_name: Optional[str] = Field(
        None, title="Substitutes all occurrences of {FULLNAME} within the content of the template with this value.",
        max_length=100
    )
    company: Optional[str] = Field(
        None, title="Substitutes all occurrences of {COMPANY} within the content of the template with this value.",
        max_length=100
    )
    position: Optional[str] = Field(
        None, title="Substitutes all occurrences of {POSITION} within the content of the template with this value.",
        max_length=100
    )


class QueryImageGenerate(BaseModel):
    """A model for submitting a batch of images to be generated from a query"""
    query_id: int = Field(
        title="ID of the query to use for generating the image. One image will be generated for each "
    )


class EmployeeImageGenerate(QueryImageGenerate):
    """A model for generating a image from a specific employee in the database"""
    employee_id: int = Field(
        title="ID of the employee to use as basis for generating the query. Employee must belong to the query."
    )


# Creates all tables, uncomment when needed to create tables
SQLModel.metadata.create_all(engine)
