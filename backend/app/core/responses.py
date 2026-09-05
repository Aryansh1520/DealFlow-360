"""Generic success-response envelope shared by every endpoint."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: T


def ok(data: T, message: str = "Success") -> SuccessResponse[T]:
    return SuccessResponse(data=data, message=message)
