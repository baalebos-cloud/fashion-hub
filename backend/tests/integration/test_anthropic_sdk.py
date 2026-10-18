"""Exercise the installed SDK and JSON contract using an in-memory transport."""
import json

import anthropic
import httpx2
import pytest

from app.core.exceptions import ExternalProviderError
from app.integrations.ai.llm_client import ChatMessage, LLMClient


@pytest.fixture()
def sdk_transport(monkeypatch):
    real_client = anthropic.Anthropic
    requests, clients = [], []
    response_status = [200]

    def respond(request):
        requests.append(json.loads(request.content))
        if response_status[0] != 200:
            return httpx2.Response(response_status[0], json={
                'type': 'error', 'error': {'type': 'api_error', 'message': 'Transport test failure'},
            })
        return httpx2.Response(200, json={
            'id': 'msg_test', 'type': 'message', 'role': 'assistant', 'model': 'claude-test',
            'content': [{'type': 'text', 'text': 'Hello from the SDK.'}],
            'stop_reason': 'end_turn', 'stop_sequence': None,
            'usage': {'input_tokens': 5, 'output_tokens': 6},
        })

    def create(**kwargs):
        http = httpx2.Client(transport=httpx2.MockTransport(respond))
        clients.append(http)
        return real_client(**kwargs, http_client=http, max_retries=0)

    monkeypatch.setattr(anthropic, 'Anthropic', create)
    return requests, clients, response_status


@pytest.mark.parametrize('has_system', [False, True])
def test_sdk_serializes_messages_and_closes_transport(sdk_transport, has_system):
    requests, clients, _ = sdk_transport
    messages = [ChatMessage('user', 'How much fabric do I need?')]
    if has_system:
        messages = [ChatMessage('system', 'Help with fashion.'), ChatMessage('system', 'Use yards.')] + messages
    result = LLMClient(api_key='test-key', model='claude-test').complete(messages, max_tokens=64)
    assert result.content == 'Hello from the SDK.'
    assert result.raw_response['id'] == 'msg_test'
    assert requests[0]['messages'] == [{'role': 'user', 'content': 'How much fabric do I need?'}]
    assert requests[0]['model'] == 'claude-test' and requests[0]['max_tokens'] == 64
    if has_system:
        assert requests[0]['system'] == 'Help with fashion.\nUse yards.'
    else:
        assert 'system' not in requests[0]
    assert clients[0].is_closed


def test_sdk_failure_is_wrapped_and_transport_is_closed(sdk_transport):
    requests, clients, response_status = sdk_transport
    response_status[0] = 500
    with pytest.raises(ExternalProviderError, match='AI provider request failed') as failure:
        LLMClient(api_key='test-key', model='claude-test').complete([ChatMessage('user', 'Hello')])
    assert isinstance(failure.value.__cause__, anthropic.InternalServerError)
    assert len(requests) == 1 and clients[0].is_closed
