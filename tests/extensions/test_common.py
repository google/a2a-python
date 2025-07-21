from a2a.extensions.common import find_extension_by_uri
from a2a.types import AgentCard, AgentExtension, AgentCapabilities


def test_find_extension_by_uri():
    ext1 = AgentExtension(uri='foo', name='Foo', description='The Foo extension')
    ext2 = AgentExtension(uri='bar', name='Bar', description='The Bar extension')
    card = AgentCard(
        agent_id='test-agent',
        name='Test Agent',
        description='Test Agent Description',
        version='1.0',
        url='http://test.com',
        skills=[],
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        capabilities=AgentCapabilities(extensions=[ext1, ext2]),
    )

    assert find_extension_by_uri(card, 'foo') == ext1
    assert find_extension_by_uri(card, 'bar') == ext2
    assert find_extension_by_uri(card, 'baz') is None


def test_find_extension_by_uri_no_extensions():
    card = AgentCard(
        agent_id='test-agent',
        name='Test Agent',
        description='Test Agent Description',
        version='1.0',
        url='http://test.com',
        skills=[],
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        capabilities=AgentCapabilities(extensions=None),
    )

    assert find_extension_by_uri(card, 'foo') is None
