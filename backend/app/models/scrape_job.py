from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class JobStatus(str, Enum):
    """Status of a scrape job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapeJobBase(BaseModel):
    """Base scrape job model."""
    urls: list[str] = Field(..., description="List of URLs to scrape")


class ScrapeJobCreate(ScrapeJobBase):
    """Model for creating a new scrape job."""
    pass


class ScrapeJobResponse(BaseModel):
    """Model for scrape job response."""
    id: str
    status: JobStatus
    urls: list[str]
    total_urls: int
    processed_urls: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScrapeJobUpdate(BaseModel):
    """Model for updating scrape job status."""
    status: Optional[JobStatus] = None
    processed_urls: Optional[int] = None
    error_message: Optional[str] = None

