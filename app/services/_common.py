from abc import ABC
from abc import abstractmethod
from typing import TypeIs

from fastapi import status

from app.adapters.boomlings import BoomlingsClient
from app.adapters.mysql import ImplementsMySQL
from app.adapters.redis import RedisClient
from app.adapters.storage import ImplementsStorage
from app.resources import AccountCommentRepository
from app.resources import AnalyticsRepository
from app.resources import ArtistRepository
from app.resources import BanRepository
from app.resources import BlockRepository
from app.resources import ChestRepository
from app.resources import CommentRepository
from app.resources import CredentialRepository
from app.resources import DeviceRepository
from app.resources import DownloadMarkRepository
from app.resources import FriendRequestRepository
from app.resources import FriendshipRepository
from app.resources import GauntletRepository
from app.resources import HealthRepository
from app.resources import LeaderboardRepository
from app.resources import LevelDataRepository
from app.resources import LevelListRepository
from app.resources import LevelRepository
from app.resources import LevelScoreRepository
from app.resources import LikeRepository
from app.resources import MapPackRepository
from app.resources import MessageRepository
from app.resources import ModActionRepository
from app.resources import PermissionRepository
from app.resources import PlatformerScoreRepository
from app.resources import QuestRepository
from app.resources import RateLimitRepository
from app.resources import ReportRepository
from app.resources import RoleRepository
from app.resources import SaveRepository
from app.resources import SecretRewardRepository
from app.resources import SessionRepository
from app.resources import SongLookupRepository
from app.resources import SongRepository
from app.resources import StarVoteRepository
from app.resources import StatsRepository
from app.resources import SuggestionRepository
from app.resources import TimelyRepository
from app.resources import UserQuestRepository
from app.resources import UserRepository

GD_FAILURE = -1


class ServiceError:
    """Mixin for the error enums: `class UserError(ServiceError, StrEnum)`.
    The alias lives here because an Enum body treats `type` statements as
    members."""

    type OnSuccess[T] = T | ServiceError

    def service(self) -> str:
        return type(self).__name__.removesuffix("Error").lower()

    def status_code(self) -> int:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    def code(self) -> int:
        """The numeric response the Geometry Dash client receives."""

        return GD_FAILURE

    def resolve_name(self) -> str:
        return f"{self.service()}.{self}"


def is_success[V](result: ServiceError.OnSuccess[V]) -> TypeIs[V]:
    return not isinstance(result, ServiceError)


def is_error[V](result: ServiceError.OnSuccess[V]) -> TypeIs[ServiceError]:
    return isinstance(result, ServiceError)


class AbstractContext(ABC):
    """Everything a service may reach: adapters through their interfaces and a
    repository per stored resource."""

    @property
    @abstractmethod
    def _mysql(self) -> ImplementsMySQL: ...

    @property
    @abstractmethod
    def _redis(self) -> RedisClient: ...

    @property
    @abstractmethod
    def storage(self) -> ImplementsStorage: ...

    @property
    @abstractmethod
    def boomlings(self) -> BoomlingsClient: ...

    @property
    def users(self) -> UserRepository:
        return UserRepository(self._mysql)

    @property
    def analytics(self) -> AnalyticsRepository:
        return AnalyticsRepository(self._mysql)

    @property
    def credentials(self) -> CredentialRepository:
        return CredentialRepository(self._mysql)

    @property
    def stats(self) -> StatsRepository:
        return StatsRepository(self._mysql)

    @property
    def saves(self) -> SaveRepository:
        return SaveRepository(self._mysql)

    @property
    def bans(self) -> BanRepository:
        return BanRepository(self._mysql)

    @property
    def devices(self) -> DeviceRepository:
        return DeviceRepository(self._mysql)

    @property
    def friendships(self) -> FriendshipRepository:
        return FriendshipRepository(self._mysql)

    @property
    def blocks(self) -> BlockRepository:
        return BlockRepository(self._mysql)

    @property
    def friend_requests(self) -> FriendRequestRepository:
        return FriendRequestRepository(self._mysql)

    @property
    def messages(self) -> MessageRepository:
        return MessageRepository(self._mysql)

    @property
    def account_comments(self) -> AccountCommentRepository:
        return AccountCommentRepository(self._mysql)

    @property
    def artists(self) -> ArtistRepository:
        return ArtistRepository(self._mysql)

    @property
    def songs(self) -> SongRepository:
        return SongRepository(self._mysql)

    @property
    def song_lookups(self) -> SongLookupRepository:
        return SongLookupRepository(self._redis)

    @property
    def levels(self) -> LevelRepository:
        return LevelRepository(self._mysql)

    @property
    def level_data(self) -> LevelDataRepository:
        return LevelDataRepository(self._mysql)

    @property
    def level_lists(self) -> LevelListRepository:
        return LevelListRepository(self._mysql)

    @property
    def map_packs(self) -> MapPackRepository:
        return MapPackRepository(self._mysql)

    @property
    def gauntlets(self) -> GauntletRepository:
        return GauntletRepository(self._mysql)

    @property
    def health(self) -> HealthRepository:
        return HealthRepository(self._mysql, self._redis)

    @property
    def timely(self) -> TimelyRepository:
        return TimelyRepository(self._mysql)

    @property
    def comments(self) -> CommentRepository:
        return CommentRepository(self._mysql)

    @property
    def likes(self) -> LikeRepository:
        return LikeRepository(self._mysql)

    @property
    def level_scores(self) -> LevelScoreRepository:
        return LevelScoreRepository(self._mysql)

    @property
    def platformer_scores(self) -> PlatformerScoreRepository:
        return PlatformerScoreRepository(self._mysql)

    @property
    def star_votes(self) -> StarVoteRepository:
        return StarVoteRepository(self._mysql)

    @property
    def suggestions(self) -> SuggestionRepository:
        return SuggestionRepository(self._mysql)

    @property
    def reports(self) -> ReportRepository:
        return ReportRepository(self._mysql)

    @property
    def quests(self) -> QuestRepository:
        return QuestRepository(self._mysql)

    @property
    def user_quests(self) -> UserQuestRepository:
        return UserQuestRepository(self._mysql)

    @property
    def chests(self) -> ChestRepository:
        return ChestRepository(self._mysql)

    @property
    def secret_rewards(self) -> SecretRewardRepository:
        return SecretRewardRepository(self._mysql)

    @property
    def mod_actions(self) -> ModActionRepository:
        return ModActionRepository(self._mysql)

    @property
    def roles(self) -> RoleRepository:
        return RoleRepository(self._mysql)

    @property
    def permissions(self) -> PermissionRepository:
        return PermissionRepository(self._mysql, self._redis)

    @property
    def leaderboards(self) -> LeaderboardRepository:
        return LeaderboardRepository(self._redis)

    @property
    def sessions(self) -> SessionRepository:
        return SessionRepository(self._redis)

    @property
    def rate_limits(self) -> RateLimitRepository:
        return RateLimitRepository(self._redis)

    @property
    def download_marks(self) -> DownloadMarkRepository:
        return DownloadMarkRepository(self._redis)
