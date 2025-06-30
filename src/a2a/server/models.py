from typing import TYPE_CHECKING, Any, Generic, TypeVar


if TYPE_CHECKING:
    from typing_extensions import override
else:

    def override(func):  # noqa: D103
        return func


from pydantic import BaseModel

from a2a.types import Artifact, Message, TaskStatus, PushNotificationAuthenticationInfo

try:
    from cryptography.fernet import Fernet
    from sqlalchemy import JSON, Dialect, String, LargeBinary    
    from sqlalchemy.orm import (
        DeclarativeBase,
        Mapped,
        declared_attr,
        mapped_column,
    )
    from sqlalchemy.types import TypeDecorator
except ImportError as e:
    raise ImportError(
        'Database models require SQLAlchemy. '
        'Install with one of: '
        "'pip install a2a-sdk[postgresql]', "
        "'pip install a2a-sdk[mysql]', "
        "'pip install a2a-sdk[sqlite]', "
        "or 'pip install a2a-sdk[sql]'"
    ) from e


T = TypeVar('T', bound=BaseModel)

_ENCRYPTION_KEY: bytes | None = None

def set_model_encryption_key(key: bytes) -> None:
    """Sets the encryption key used for encrypting model data in the database."""
    global _ENCRYPTION_KEY
    _ENCRYPTION_KEY = key

class PydanticType(TypeDecorator[T], Generic[T]):
    """SQLAlchemy type that handles Pydantic model serialization."""

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_type: type[T], **kwargs: dict[str, Any]):
        self.pydantic_type = pydantic_type
        super().__init__(**kwargs)

    @override
    def process_bind_param(
        self, value: T | None, dialect: Dialect
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return (
            value.model_dump(mode='json')
            if isinstance(value, BaseModel)
            else value
        )

    @override
    def process_result_value(
        self, value: dict[str, Any] | None, dialect: Dialect
    ) -> T | None:
        if value is None:
            return None
        return self.pydantic_type.model_validate(value)

class EncryptedPydanticType(TypeDecorator[T], Generic[T]):
    """SQLAlchemy type that handles Pydantic model serialization with encryption."""

    impl = LargeBinary # Store encrypted data as binary
    cache_ok = True

    def __init__(self, pydantic_type: type[T], **kwargs: Any):
        super().__init__(**kwargs)        
        if _ENCRYPTION_KEY is None:
            raise RuntimeError(
                "Encryption key not set for models. "
                "Call a2a.server.models.set_model_encryption_key(key) before model definition or usage."
            )
        self.pydantic_type = pydantic_type
        self.fernet = Fernet(_ENCRYPTION_KEY)

    @override
    def process_bind_param(
        self, value: T | None, dialect: Dialect
    ) -> bytes | None:
        if value is None:
            return None
        # Pydantic model to JSON string, then encode to bytes for encryption
        json_string = value.model_dump_json()
        encrypted_data = self.fernet.encrypt(json_string.encode('utf-8'))
        return encrypted_data

    @override
    def process_result_value(
        self, value: bytes | None, dialect: Dialect
    ) -> T | None:
        if value is None:
            return None
        # Decrypt bytes to JSON string, then parse with Pydantic
        decrypted_json_string = self.fernet.decrypt(value).decode('utf-8')
        return self.pydantic_type.model_validate_json(decrypted_json_string)

class PydanticListType(TypeDecorator[list[T]], Generic[T]):
    """SQLAlchemy type that handles lists of Pydantic models."""

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_type: type[T], **kwargs: dict[str, Any]):
        self.pydantic_type = pydantic_type
        super().__init__(**kwargs)

    @override
    def process_bind_param(
        self, value: list[T] | None, dialect: Dialect
    ) -> list[dict[str, Any]] | None:
        if value is None:
            return None
        return [
            item.model_dump(mode='json')
            if isinstance(item, BaseModel)
            else item
            for item in value
        ]

    @override
    def process_result_value(
        self, value: list[dict[str, Any]] | None, dialect: Dialect
    ) -> list[T] | None:
        if value is None:
            return None
        return [self.pydantic_type.model_validate(item) for item in value]


# Base class for all database models
class Base(DeclarativeBase):
    """Base class for declarative models in A2A SDK."""


# TaskMixin that can be used with any table name
class TaskMixin:
    """Mixin providing standard task columns with proper type handling."""

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    contextId: Mapped[str] = mapped_column(String, nullable=False)  # noqa: N815
    kind: Mapped[str] = mapped_column(String, nullable=False, default='task')

    # Properly typed Pydantic fields with automatic serialization
    status: Mapped[TaskStatus] = mapped_column(PydanticType(TaskStatus))
    artifacts: Mapped[list[Artifact] | None] = mapped_column(
        PydanticListType(Artifact), nullable=True
    )
    history: Mapped[list[Message] | None] = mapped_column(
        PydanticListType(Message), nullable=True
    )

    # Using declared_attr to avoid conflict with Pydantic's metadata
    @declared_attr
    @classmethod
    def task_metadata(cls) -> Mapped[dict[str, Any] | None]:
        return mapped_column(JSON, nullable=True, name='metadata')

    @override
    def __repr__(self) -> str:
        """Return a string representation of the task."""
        repr_template = (
            '<{CLS}(id="{ID}", contextId="{CTX_ID}", status="{STATUS}")>'
        )
        return repr_template.format(
            CLS=self.__class__.__name__,
            ID=self.id,
            CTX_ID=self.contextId,
            STATUS=self.status,
        )


def create_task_model(
    table_name: str = 'tasks', base: type[DeclarativeBase] = Base
) -> type:
    """Create a TaskModel class with a configurable table name.

    Args:
        table_name: Name of the database table. Defaults to 'tasks'.
        base: Base declarative class to use. Defaults to the SDK's Base class.

    Returns:
        TaskModel class with the specified table name.

    Example:
        # Create a task model with default table name
        TaskModel = create_task_model()

        # Create a task model with custom table name
        CustomTaskModel = create_task_model('my_tasks')

        # Use with a custom base
        from myapp.database import Base as MyBase
        TaskModel = create_task_model('tasks', MyBase)
    """

    class TaskModel(TaskMixin, base): # type: ignore
        __tablename__ = table_name

        @override
        def __repr__(self) -> str:
            """Return a string representation of the task."""
            repr_template = '<TaskModel[{TABLE}](id="{ID}", contextId="{CTX_ID}", status="{STATUS}")>'
            return repr_template.format(
                TABLE=table_name,
                ID=self.id,
                CTX_ID=self.contextId,
                STATUS=self.status,
            )

    # Set a dynamic name for better debugging
    TaskModel.__name__ = f'TaskModel_{table_name}'
    TaskModel.__qualname__ = f'TaskModel_{table_name}'

    return TaskModel


# Default TaskModel for backward compatibility
class TaskModel(TaskMixin, Base):
    """Default task model with standard table name."""

    __tablename__ = 'tasks'


class PushNotificationConfigMixin:
    """Mixin providing standard columns for push notification configuration."""
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    task_id: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str | None] = mapped_column(String, nullable=True)
    authentication: Mapped[PushNotificationAuthenticationInfo | None] = mapped_column(
        EncryptedPydanticType(PushNotificationAuthenticationInfo), nullable=True
    )

    @override
    def __repr__(self) -> str:
        """Return a string representation of the push notification config."""
        repr_template = (
            '<{CLS}(id="{ID}", task_id="{TASK_ID}", url="{URL}")>'
        )
        return repr_template.format(
            CLS=self.__class__.__name__,
            ID=self.id,
            TASK_ID=self.task_id,
            URL=self.url,
        )

def create_push_notification_config_model(
    table_name: str = 'push_notification_configs',
    base: type[DeclarativeBase] = Base
) -> type:
    """Create a PushNotificationConfigModel class with a configurable table name.

    Args:
        table_name: Name of the database table. Defaults to 'push_notification_configs'.
        base: Base declarative class to use. Defaults to the SDK's Base class.

    Returns:
        PushNotificationConfigModel class with the specified table name.
    """

    class PushNotificationConfigModel(PushNotificationConfigMixin, base): # type: ignore
        __tablename__ = table_name

    PushNotificationConfigModel.__name__ = f'PushNotificationConfigModel_{table_name}'
    PushNotificationConfigModel.__qualname__ = f'PushNotificationConfigModel_{table_name}'
    return PushNotificationConfigModel