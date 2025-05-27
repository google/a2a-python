try:
    from sqlalchemy import JSON, Column, String
    from sqlalchemy.orm import declarative_base
except ImportError as e:
    raise ImportError(
        'Database models require SQLAlchemy. '
        'Install with one of: '
        "'pip install a2a-sdk[postgresql]', "
        "'pip install a2a-sdk[mysql]', "
        "'pip install a2a-sdk[sqlite]', "
        "or 'pip install a2a-sdk[sql]'"
    ) from e


Base = declarative_base()


class TaskModel(Base):
    __tablename__ = 'tasks'

    id = Column(String, primary_key=True, index=True)
    contextId = Column(String, nullable=False)
    kind = Column(String, nullable=False, default='task')

    # Using generic JSON type for database-agnostic storage
    # This works with PostgreSQL, MySQL, SQLite, and other databases
    status = Column(JSON)  # Stores TaskStatus as JSON
    artifacts = Column(JSON, nullable=True)  # Stores list[Artifact] as JSON
    history = Column(JSON, nullable=True)  # Stores list[Message] as JSON
    task_metadata = Column(
        JSON, nullable=True, name='metadata'
    )  # Stores dict[str, Any] as JSON

    def __repr__(self):
        return f"<TaskModel(id='{self.id}', contextId='{self.contextId}', status='{self.status}')>"
