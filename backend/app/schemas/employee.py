from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmployeeCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    designation_id: int
    department_id: int | None = None
    employee_category_id: int | None = None
    trade_id: int | None = None
    employment_source: str = Field(default="in_house")
    resource_provider_id: int | None = None
    employment_status: str = Field(default="active")
    join_date: datetime | None = None
    termination_date: datetime | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    designation_id: int | None = None
    department_id: int | None = None
    employee_category_id: int | None = None
    trade_id: int | None = None
    employment_source: str | None = None
    resource_provider_id: int | None = None
    employment_status: str | None = None
    join_date: datetime | None = None
    termination_date: datetime | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class EmployeeListItem(BaseModel):
    id: int
    employee_id: str
    full_name: str
    designation_id: int
    employment_source: str
    employment_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeDetail(BaseModel):
    id: int
    employee_id: str
    full_name: str
    first_name: str | None
    middle_name: str | None
    last_name: str | None
    designation_id: int
    department_id: int | None
    employee_category_id: int | None
    trade_id: int | None
    employment_source: str
    resource_provider_id: int | None
    employment_status: str
    join_date: datetime | None
    termination_date: datetime | None
    email: str | None
    phone: str | None
    notes: str | None
    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
