from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.project import Project, ProjectApprover, ProjectMembership
from app.models.reference import (
    Department,
    Designation,
    EmployeeCategory,
    Trade,
    ResourceProvider,
)
from app.models.employee import Employee


def _to_list_item(project: Project) -> ProjectListItem:
    return ProjectListItem(
        id=project.id,
        code=project.code,
        name=project.name,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at,
    )


def _to_detail(project: Project) -> ProjectDetail:
    return ProjectDetail(
        id=project.id,
        code=project.code,
        name=project.name,
        client_name=project.client_name,
        location=project.location,
        description=project.description,
        status=project.status,
        tender_start_date=project.tender_start_date,
        tender_submission_date=project.tender_submission_date,
        expected_award_date=project.expected_award_date,
        planned_start_date=project.planned_start_date,
        planned_end_date=project.planned_end_date,
        actual_start_date=project.actual_start_date,
        actual_end_date=project.actual_end_date,
        award_probability=project.award_probability,
        archived_at=project.archived_at,
        created_by_id=project.created_by_id,
        updated_by_id=project.updated_by_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def _to_list_item(project: Project) -> ProjectListItem:
    return ProjectListItem(
        id=project.id,
        code=project.code,
        name=project.name,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at,
    )


def _to_detail(project: Project) -> ProjectDetail:
    return ProjectDetail(
        id=project.id,
        code=project.code,
        name=project.name,
        client_name=project.client_name,
        location=project.location,
        description=project.description,
        status=project.status,
        tender_start_date=project.tender_start_date,
        tender_submission_date=project.tender_submission_date,
        expected_award_date=project.expected_award_date,
        planned_start_date=project.planned_start_date,
        planned_end_date=project.planned_end_date,
        actual_start_date=project.actual_start_date,
        actual_end_date=project.actual_end_date,
        award_probability=project.award_probability,
        archived_at=project.archived_at,
        created_by_id=project.created_by_id,
        updated_by_id=project.updated_by_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


class ProjectListItem(BaseModel):
    id: int
    code: str
    name: str
    status: str
    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectDetail(BaseModel):
    id: int
    code: str
    name: str
    client_name: str | None
    location: str | None
    description: str | None
    status: str
    tender_start_date: datetime | None
    tender_submission_date: datetime | None
    expected_award_date: datetime | None
    planned_start_date: datetime | None
    planned_end_date: datetime | None
    actual_start_date: datetime | None
    actual_end_date: datetime | None
    award_probability: float | None
    archived_at: datetime | None
    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    client_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str = Field(default="tender")
    tender_start_date: datetime | None = None
    tender_submission_date: datetime | None = None
    expected_award_date: datetime | None = None
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    actual_start_date: datetime | None = None
    actual_end_date: datetime | None = None
    award_probability: float | None = None


class ProjectUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    client_name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = None
    tender_start_date: datetime | None = None
    tender_submission_date: datetime | None = None
    expected_award_date: datetime | None = None
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    actual_start_date: datetime | None = None
    actual_end_date: datetime | None = None
    award_probability: float | None = None


class ProjectMembershipCreate(BaseModel):
    user_id: int
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool = True


class ProjectMembershipUpdate(BaseModel):
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool | None = None


class ProjectMembershipResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    valid_from: datetime | None
    valid_to: datetime | None
    is_active: bool
    created_by_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectApproverApprovalType(str):
    pass


class ProjectApproverCreate(BaseModel):
    user_id: int
    approval_type: str = Field(min_length=1, max_length=20)
    sequence_order: int = Field(default=1, ge=1)
    is_required: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool = True


class ProjectApproverUpdate(BaseModel):
    approval_type: str | None = Field(default=None, min_length=1, max_length=20)
    sequence_order: int | None = Field(default=None, ge=1)
    is_required: bool | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool | None = None


class ProjectApproverResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    approval_type: str
    sequence_order: int
    is_required: bool
    valid_from: datetime | None
    valid_to: datetime | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0)


class DepartmentUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DesignationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    department_id: int | None = None
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int = Field(default=0)


class DesignationUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    department_id: int | None = None
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = None
    is_active: bool | None = None


class DesignationResponse(BaseModel):
    id: int
    code: str
    name: str
    department_id: int | None
    description: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeCategoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class EmployeeCategoryUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class EmployeeCategoryResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TradeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)


class TradeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class TradeResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceProviderCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class ResourceProviderUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    contact_person: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class ResourceProviderResponse(BaseModel):
    id: int
    code: str
    name: str
    legal_name: str | None
    contact_person: str | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    created_by_id: int
    updated_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
