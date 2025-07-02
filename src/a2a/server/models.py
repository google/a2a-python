from typing import TYPE_CHECKING, Any, Generic, TypeVar


if TYPE_CHECKING:
    from typing_extensions import override
else:

    def override(func):  # noqa: ANN001, ANN201
        """Override decorator."""
        return func


from pydantic import BaseModel

from a2a.types import Artifact, Message, TaskStatus


try:
    from sqlalchemy import JSON, Dialect, String
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


class PydanticType(TypeDecorator[T], Generic[T]):
    """SQLAlchemy type that handles Pydantic model serialization."""

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_type: type[T], **kwargs: dict[str, Any]):
        """Initialize the PydanticType.

        Args:
            pydantic_type: The Pydantic model type to handle.
            **kwargs: Additional arguments for TypeDecorator.
        """
        self.pydantic_type = pydantic_type
        super().__init__(**kwargs)

    def process_bind_param(
        self, value: T | None, dialect: Dialect
    ) -> dict[str, Any] | None:
        """Convert Pydantic model to a JSON-serializable dictionary for the database."""
        if value is None:
            return None
        return (
            value.model_dump(mode='json')
            if isinstance(value, BaseModel)
            else value
        )

    def process_result_value(
        self, value: dict[str, Any] | None, dialect: Dialect
    ) -> T | None:
        """Convert a JSON-like dictionary from the database back to a Pydantic model."""
        if value is None:
            return None
        return self.pydantic_type.model_validate(value)


class PydanticListType(TypeDecorator, Generic[T]):
    """SQLAlchemy type that handles lists of Pydantic models."""

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_type: type[T], **kwargs: dict[str, Any]):
        """Initialize the PydanticListType.

        Args:
            pydantic_type: The Pydantic model type for items in the list.
            **kwargs: Additional arguments for TypeDecorator.
        """
        self.pydantic_type = pydantic_type
        super().__init__(**kwargs)

    def process_bind_param(
        self, value: list[T] | None, dialect: Dialect
    ) -> list[dict[str, Any]] | None:
        """Convert a list of Pydantic models to a JSON-serializable list for the DB."""
        if value is None:
            return None
        return [
            item.model_dump(mode='json')
            if isinstance(item, BaseModel)
            else item
            for item in value
        ]

    def process_result_value(
        self, value: list[dict[str, Any]] | None, dialect: Dialect
    ) -> list[T] | None:
        """Convert a JSON-like list from the DB back to a list of Pydantic models."""
        if value is None:
            return None
        return [self.pydantic_type.model_validate(item) for item in value]


# Base class for all database models
class Base(DeclarativeBase):
    """Base class for declarative models in A2A SDK."""


# TaskMixin that can be used with any table name
class TaskMixin:
    """Mixin providing standard task columns with proper type handling."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    contextId: Mapped[str] = mapped_column(String(36), nullable=False)  # noqa: N815
    kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default='task'
    )

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
        """Define the 'metadata' column, avoiding name conflicts with Pydantic."""
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

    class TaskModel(TaskMixin, base):
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
