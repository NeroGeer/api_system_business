from pydantic import BaseModel, ConfigDict, Field, field_validator
from enum import Enum


class StageType(str, Enum):
    """Structural role of a stage. Names are user-editable; types are not."""
    OPEN = "OPEN"
    MIDDLE = "MIDDLE"
    END = "END"


class StageSchemaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: StageType
    name: str
    position: int

    @classmethod
    def from_orm_stage(cls, stage):
        return cls(
            id=stage.id,
            type=stage.stage_type,
            name=stage.name,
            position=stage.position,
        )


class StageSchema(BaseModel):
    team_id: int
    stages: list[StageSchemaRead]


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    position: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Stage name cannot be empty")
        return value


class UpdateStageRename(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Stage name cannot be empty")
        return value


class TransitionItem(BaseModel):
    # "from" is a reserved Python keyword; API JSON still uses the key "from".
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    from_: int = Field(alias="from", gt=0)
    to: int = Field(gt=0)


class TransitionReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transitions: list[TransitionItem] = Field(default_factory=list)


class ConfigRead(StageSchema):
    transitions: list[TransitionItem]
