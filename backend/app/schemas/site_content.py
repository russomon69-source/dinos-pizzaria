from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field


class SiteContentItem(BaseModel):
    key: str = Field(..., min_length=2, max_length=80)
    value: str = Field(..., max_length=1000)


class SiteContentUpdate(BaseModel):
    items: List[SiteContentItem] = Field(..., min_length=1, max_length=80)


class SiteContentOut(SiteContentItem):
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
