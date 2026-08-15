from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MeetingCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)

    start_time: datetime
    end_time: datetime

    participants: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_time(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        if self.end_time - self.start_time > timedelta(hours=24):
            raise ValueError("The duration between start_time and end_time cannot exceed 24 hours")

        return self


class MeetingParticipantOutSchema(BaseModel):
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class MeetingOutSchema(BaseModel):
    id: int
    team_id: int
    creator_id: int

    title: str
    description: str

    start_time: datetime
    end_time: datetime
    created_at: datetime

    participants: list[MeetingParticipantOutSchema]

    model_config = ConfigDict(from_attributes=True)


class MeetingUpdateSchema(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, min_length=1)

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    participants: Optional[list[int]] = None

    @model_validator(mode="after")
    def validate_time(self):
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time")
            if self.end_time - self.start_time > timedelta(hours=24):
                raise ValueError("The duration between start_time and end_time cannot exceed 24 hours")
        return self
