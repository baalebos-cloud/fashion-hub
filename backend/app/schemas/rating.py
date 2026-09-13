from pydantic import BaseModel


class RatingBreakdownResponse(BaseModel):
    average: float
    count: int
    distribution: dict[int, int]
