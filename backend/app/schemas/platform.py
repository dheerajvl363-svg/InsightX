from pydantic import BaseModel, ConfigDict, Field


class PlatformResponse(BaseModel):
    """Schema for platform representation in API responses."""
    id: int = Field(..., description="Unique platform ID")
    name: str = Field(..., description="Canonical platform name")

    model_config = ConfigDict(from_attributes=True)
