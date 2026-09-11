import hmac
from enum import StrEnum

from fastapi import status

from app import settings
from app.services._common import ServiceError


class AdminError(ServiceError, StrEnum):
    DISABLED = "disabled"
    UNAUTHORISED = "unauthorised"

    def service(self) -> str:
        return "admin"

    def status_code(self) -> int:
        match self:
            case AdminError.DISABLED:
                return status.HTTP_404_NOT_FOUND
            case AdminError.UNAUTHORISED:
                return status.HTTP_401_UNAUTHORIZED


def verify_key(presented: str | None) -> AdminError.OnSuccess[None]:
    if not settings.APP_ADMIN_API_KEY:
        return AdminError.DISABLED

    if presented is None or not hmac.compare_digest(
        presented, settings.APP_ADMIN_API_KEY
    ):
        return AdminError.UNAUTHORISED

    return None
