from enum import StrEnum

from fastapi import status

from app.services._common import AbstractContext
from app.services._common import ServiceError


class HealthError(ServiceError, StrEnum):
    MYSQL_UNAVAILABLE = "mysql_unavailable"
    REDIS_UNAVAILABLE = "redis_unavailable"

    def service(self) -> str:
        return "health"

    def status_code(self) -> int:
        return status.HTTP_503_SERVICE_UNAVAILABLE


async def check(ctx: AbstractContext) -> HealthError.OnSuccess[None]:
    if not await ctx.health.mysql_available():
        return HealthError.MYSQL_UNAVAILABLE

    if not await ctx.health.redis_available():
        return HealthError.REDIS_UNAVAILABLE

    return None
