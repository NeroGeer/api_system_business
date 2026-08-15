from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from src.scheme.schemas_team import TeamMemberSchema
from src.scheme.schemas_user import RoleSchema


class AdminScheme(BaseModel):
    id: int
    email: EmailStr
    roles: List[RoleSchema]

    team_memberships: List[TeamMemberSchema] = Field(
        default_factory=list, validation_alias="team_memberships"
    )


class AdminTeamCrateSchema(BaseModel):
    name: str
    invite_code: str


class OutAdminTeamCrateSchema(BaseModel):
    id: int
    name: str
    invite_code: str
