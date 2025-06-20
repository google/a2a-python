import uuid

from unittest.mock import Mock, patch

import pytest

from a2a.server.agent_execution import RequestContext
from a2a.types import (
    Message,
    MessageSendParams,
    Task,
)


class TestRequestContext:
    """Tests for the RequestContext class."""

    @pytest.fixture
    def mock_message(self):
        """Fixture for a mock Message."""
        return Mock(spec=Message, task_id=None, context_id=None)

    @pytest.fixture
    def mock_params(self, mock_message):
        """Fixture for a mock MessageSendParams."""
        return Mock(spec=MessageSendParams, message=mock_message)

    @pytest.fixture
    def mock_task(self):
        """Fixture for a mock Task."""
        return Mock(spec=Task, id='task-123', context_id='context-456')

    def test_init_without_params(self):
        """Test initialization without parameters."""
        context = RequestContext()
        assert context.message is None
        assert context.task_id is None
        assert context.context_id is None
        assert context.current_task is None
        assert context.related_tasks == []

    def test_init_with_params_no_ids(self, mock_params):
        """Test initialization with params but no task or context IDs."""
        with patch(
            'uuid.uuid4',
            side_effect=[
                uuid.UUID('00000000-0000-0000-0000-000000000001'),
                uuid.UUID('00000000-0000-0000-0000-000000000002'),
            ],
        ):
            context = RequestContext(request=mock_params)

        assert context.message == mock_params.message
        assert context.task_id == '00000000-0000-0000-0000-000000000001'
        assert (
            mock_params.message.task_id
            == '00000000-0000-0000-0000-000000000001'
        )
        assert context.context_id == '00000000-0000-0000-0000-000000000002'
        assert (
            mock_params.message.context_id
            == '00000000-0000-0000-0000-000000000002'
        )

    def test_init_with_task_id(self, mock_params):
        """Test initialization with task ID provided."""
        task_id = 'task-123'
        context = RequestContext(request=mock_params, task_id=task_id)

        assert context.task_id == task_id
        assert mock_params.message.task_id == task_id

    def test_init_with_context_id(self, mock_params):
        """Test initialization with context ID provided."""
        context_id = 'context-456'
        context = RequestContext(request=mock_params, context_id=context_id)

        assert context.context_id == context_id
        assert mock_params.message.context_id == context_id

    def test_init_with_both_ids(self, mock_params):
        """Test initialization with both task and context IDs provided."""
        task_id = 'task-123'
        context_id = 'context-456'
        context = RequestContext(
            request=mock_params, task_id=task_id, context_id=context_id
        )

        assert context.task_id == task_id
        assert mock_params.message.task_id == task_id
        assert context.context_id == context_id
        assert mock_params.message.context_id == context_id

    def test_init_with_task(self, mock_params, mock_task):
        """Test initialization with a task object."""
        context = RequestContext(request=mock_params, task=mock_task)

        assert context.current_task == mock_task

    def test_get_user_input_no_params(self):
        """Test get_user_input with no params returns empty string."""
        context = RequestContext()
        assert context.get_user_input() == ''

    def test_attach_related_task(self, mock_task):
        """Test attach_related_task adds a task to related_tasks."""
        context = RequestContext()
        assert len(context.related_tasks) == 0

        context.attach_related_task(mock_task)
        assert len(context.related_tasks) == 1
        assert context.related_tasks[0] == mock_task

        # Test adding multiple tasks
        another_task = Mock(spec=Task)
        context.attach_related_task(another_task)
        assert len(context.related_tasks) == 2
        assert context.related_tasks[1] == another_task

    def test_current_task_property(self, mock_task):
        """Test current_task getter and setter."""
        context = RequestContext()
        assert context.current_task is None

        context.current_task = mock_task
        assert context.current_task == mock_task

        # Change current task
        new_task = Mock(spec=Task)
        context.current_task = new_task
        assert context.current_task == new_task

    def test_check_or_generate_task_id_no_params(self):
        """Test _check_or_generate_task_id with no params does nothing."""
        context = RequestContext()
        context._check_or_generate_task_id()
        assert context.task_id is None

    def test_check_or_generate_task_id_with_existing_task_id(self, mock_params):
        """Test _check_or_generate_task_id with existing task ID."""
        existing_id = 'existing-task-id'
        mock_params.message.task_id = existing_id

        context = RequestContext(request=mock_params)
        # The method is called during initialization

        assert context.task_id == existing_id
        assert mock_params.message.task_id == existing_id

    def test_check_or_generate_context_id_no_params(self):
        """Test _check_or_generate_context_id with no params does nothing."""
        context = RequestContext()
        context._check_or_generate_context_id()
        assert context.context_id is None

    def test_check_or_generate_context_id_with_existing_context_id(
        self, mock_params
    ):
        """Test _check_or_generate_context_id with existing context ID."""
        existing_id = 'existing-context-id'
        mock_params.message.context_id = existing_id

        context = RequestContext(request=mock_params)
        # The method is called during initialization

        assert context.context_id == existing_id
        assert mock_params.message.context_id == existing_id

    def test_with_related_tasks_provided(self, mock_task):
        """Test initialization with related tasks provided."""
        related_tasks = [mock_task, Mock(spec=Task)]
        context = RequestContext(related_tasks=related_tasks)

        assert context.related_tasks == related_tasks
        assert len(context.related_tasks) == 2

    def test_message_property_without_params(self):
        """Test message property returns None when no params are provided."""
        context = RequestContext()
        assert context.message is None

    def test_message_property_with_params(self, mock_params):
        """Test message property returns the message from params."""
        context = RequestContext(request=mock_params)
        assert context.message == mock_params.message

    def test_init_with_existing_ids_in_message(self, mock_message, mock_params):
        """Test initialization with existing IDs in the message."""
        mock_message.task_id = 'existing-task-id'
        mock_message.context_id = 'existing-context-id'

        context = RequestContext(request=mock_params)

        assert context.task_id == 'existing-task-id'
        assert context.context_id == 'existing-context-id'
        # No new UUIDs should be generated

    def test_init_with_task_id_and_existing_task_id_match(
        self, mock_params, mock_task
    ):
        """Test initialization succeeds when task_id matches task.id."""
        mock_params.message.task_id = mock_task.id

        context = RequestContext(
            request=mock_params, task_id=mock_task.id, task=mock_task
        )

        assert context.task_id == mock_task.id
        assert context.current_task == mock_task

    def test_init_with_context_id_and_existing_context_id_match(
        self, mock_params, mock_task
    ):
        """Test initialization succeeds when context_id matches task.context_id."""
        mock_params.message.task_id = mock_task.id  # Set matching task ID
        mock_params.message.context_id = mock_task.context_id

        context = RequestContext(
            request=mock_params,
            task_id=mock_task.id,
            context_id=mock_task.context_id,
            task=mock_task,
        )

        assert context.context_id == mock_task.context_id
        assert context.current_task == mock_task
