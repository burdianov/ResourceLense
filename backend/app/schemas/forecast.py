from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# --- writes ----------------------------------------------------------------


class ForecastMonthCellInput(BaseModel):
    month: date
    allocation_percentage: float = Field(ge=0, le=100)


class ForecastLineCreate(BaseModel):
    designation_id: int
    employee_id: int | None = None
    headcount: int = Field(default=1, ge=1)
    notes: str | None = Field(default=None, max_length=1000)
    sort_order: int = Field(default=0, ge=0)
    months: list[ForecastMonthCellInput] = Field(default_factory=list)


class ForecastLineUpdate(BaseModel):
    designation_id: int | None = None
    employee_id: int | None = None
    headcount: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = Field(default=None, ge=0)


class ForecastMonthsUpdate(BaseModel):
    months: list[ForecastMonthCellInput] = Field(min_length=1)


class ForecastVersionCreate(BaseModel):
    project_id: int
    forecast_type: str
    name: str | None = Field(default=None, max_length=255)
    forecast_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)


class ForecastVersionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    forecast_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)


class ForecastCloneRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)


# --- reads -----------------------------------------------------------------


class ForecastVersionListItem(BaseModel):
    id: int
    project_id: int
    forecast_type: str
    version_no: int
    name: str | None
    status: str
    forecast_date: date | None
    is_current: bool
    created_at: datetime
    published_at: datetime | None
    superseded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ForecastMonthCell(BaseModel):
    month: date
    allocation_percentage: float
    fte: float
    hours: float

    # Cost view — only populated for users with forecasts.cost.view.
    hourly_rate: float | None = None
    currency_code: str | None = None
    rate_source: str | None = None
    cost: float | None = None
    missing_rate: bool | None = None


class ForecastLineSummary(BaseModel):
    active_months: int
    average_fte: float
    total_hours: float


class ForecastLineResponse(BaseModel):
    id: int
    designation_id: int
    designation_name: str
    employee_id: int | None
    employee_code: str | None
    employee_name: str | None
    headcount: int
    notes: str | None
    sort_order: int
    months: list[ForecastMonthCell]
    summary: ForecastLineSummary


class ForecastVersionDetail(ForecastVersionListItem):
    description: str | None
    created_by_id: int
    published_by_id: int | None
    lines: list[ForecastLineResponse]
