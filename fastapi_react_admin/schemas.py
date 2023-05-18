from pydantic import BaseModel
from typing import Optional, Any

class RaResponseModel(BaseModel):
    data: Any
    total: Optional[int]=None
