from core.app.entities.app_invoke_entities import InvokeFrom
from core.workflow.enums import SystemVariableKey
from core.workflow.graph_engine.entities.event import (
    GraphRunSucceededEvent,
    NodeRunExceptionEvent,
    NodeRunStreamChunkEvent,
)
from core.workflow.graph_engine.entities.graph import Graph
from core.workflow.graph_engine.graph_engine import GraphEngine
from models.enums import UserFrom
from models.workflow import WorkflowType


class ContinueOnErrorTestHelper:
    @staticmethod
    def get_code_node(code: str, error_strategy: str = "fail-branch", default_value: dict | None = None):
        """Helper method to create a code node configuration"""
        node = {
            "id": "node",
            "data": {
                "outputs": {"result": {"type": "number"}},
                "error_strategy": error_strategy,
                "title": "code",
                "variables": [],
                "code_language": "python3",
                "code": "\n".join([line[4:] for line in code.split("\n")]),
                "type": "code",
            },
        }
        if default_value:
            node["data"]["default_value"] = default_value
        return node

    @staticmethod
    def get_http_node(error_strategy: str = "fail-branch", default_value: dict | None = None):
        """Helper method to create a http node configuration"""
        node = {
            "id": "node",
            "data": {
                "title": "http",
                "desc": "",
                "method": "get",
                "url": "http://example.com",
                "authorization": {
                    "type": "api-key",
                    # missing config field
                },
                "headers": "X-Header:123",
                "params": "A:b",
                "body": None,
                "type": "http-request",
                "error_strategy": error_strategy,
            },
        }
        if default_value:
            node["data"]["default_value"] = default_value
        return node

    @staticmethod
    def get_tool_node(error_strategy: str = "fail-branch", default_value: dict | None = None):
        """Helper method to create a tool node configuration"""
        node = {
            "id": "node",
            "data": {
                "title": "a",
                "desc": "a",
                "provider_id": "maths",
                "provider_type": "builtin",
                "provider_name": "maths",
                "tool_name": "eval_expression",
                "tool_label": "eval_expression",
                "tool_configurations": {},
                "tool_parameters": {
                    "expression": {
                        "type": "variable",
                        "value": ["1", "123", "args1"],
                    }
                },
                "type": "tool",
                "error_strategy": error_strategy,
            },
        }
        if default_value:
            node["data"]["default_value"] = default_value
        return node

    @staticmethod
    def get_llm_node(error_strategy: str = "fail-branch", default_value: dict | None = None):
        """Helper method to create a llm node configuration"""
        node = {
            "id": "node",
            "data": {
                "title": "123",
                "type": "llm",
                "model": {"provider": "openai", "name": "gpt-3.5-turbo", "mode": "chat", "completion_params": {}},
                "prompt_template": [
                    {"role": "system", "text": "you are a helpful assistant.\ntoday's weather is {{#abc.output#}}."},
                    {"role": "user", "text": "{{#sys.query#}}"},
                ],
                "memory": None,
                "context": {"enabled": False},
                "vision": {"enabled": False},
                "error_strategy": error_strategy,
            },
        }
        if default_value:
            node["data"]["default_value"] = default_value
        return node

    @staticmethod
    def create_test_graph_engine(graph_config: dict, user_inputs: dict | None = None):
        """Helper method to create a graph engine instance for testing"""
        graph = Graph.init(graph_config=graph_config)
        variable_pool = {
            "system_variables": {
                SystemVariableKey.QUERY: "clear",
                SystemVariableKey.FILES: [],
                SystemVariableKey.CONVERSATION_ID: "abababa",
                SystemVariableKey.USER_ID: "aaa",
            },
            "user_inputs": user_inputs or {"uid": "takato"},
        }

        return GraphEngine(
            tenant_id="111",
            app_id="222",
            workflow_type=WorkflowType.CHAT,
            workflow_id="333",
            graph_config=graph_config,
            user_id="444",
            user_from=UserFrom.ACCOUNT,
            invoke_from=InvokeFrom.WEB_APP,
            call_depth=0,
            graph=graph,
            variable_pool=variable_pool,
            max_execution_steps=500,
            max_execution_time=1200,
        )


DEFAULT_VALUE_EDGE = [
    {
        "id": "start-source-node-target",
        "source": "start",
        "target": "node",
        "sourceHandle": "source",
    },
    {
        "id": "node-source-answer-target",
        "source": "node",
        "target": "answer",
        "sourceHandle": "source",
    },
]

FAIL_BRANCH_EDGES = [
    {
        "id": "start-source-node-target",
        "source": "start",
        "target": "node",
        "sourceHandle": "source",
    },
    {
        "id": "node-true-success-target",
        "source": "node",
        "target": "success",
        "sourceHandle": "source",
        "errorHandle": "false",
    },
    {
        "id": "node-false-error-target",
        "source": "node",
        "target": "error",
        "sourceHandle": "source",
        "errorHandle": "true",
    },
]


def test_code_default_value_continue_on_error():
    error_code = """
    def main() -> dict:
        return {
            "result": 1 / 0,
        }
    """

    graph_config = {
        "edges": DEFAULT_VALUE_EDGE,
        "nodes": [
            {"data": {"title": "start", "type": "start", "variables": []}, "id": "start"},
            {"data": {"title": "answer", "type": "answer", "answer": "{{#node.result#}}"}, "id": "answer"},
            ContinueOnErrorTestHelper.get_code_node(error_code, "default-value", {"result": 132123}),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "132123"} for e in events)
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_code_fail_branch_continue_on_error():
    error_code = """
    def main() -> dict:
        return {
            "result": 1 / 0,
        }
    """

    graph_config = {
        "edges": FAIL_BRANCH_EDGES,
        "nodes": [
            {"data": {"title": "Start", "type": "start", "variables": []}, "id": "start"},
            {
                "data": {"title": "success", "type": "answer", "answer": "node node run successfully"},
                "id": "success",
            },
            {
                "data": {"title": "error", "type": "answer", "answer": "node node run failed"},
                "id": "error",
            },
            ContinueOnErrorTestHelper.get_code_node(error_code),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1
    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(
        isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "node node run failed"} for e in events
    )


def test_code_success_branch_continue_on_error():
    success_code = """
    def main() -> dict:
        return {
            "result": 1 / 1,
        }
    """

    graph_config = {
        "edges": FAIL_BRANCH_EDGES,
        "nodes": [
            {"data": {"title": "Start", "type": "start", "variables": []}, "id": "start"},
            ContinueOnErrorTestHelper.get_code_node(success_code),
            {
                "data": {"title": "success", "type": "answer", "answer": "node node run successfully"},
                "id": "success",
            },
            {
                "data": {"title": "error", "type": "answer", "answer": "node node run failed"},
                "id": "error",
            },
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(
        isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "node node run successfully"} for e in events
    )
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_http_node_default_value_continue_on_error():
    """Test HTTP node with default value error strategy"""
    graph_config = {
        "edges": DEFAULT_VALUE_EDGE,
        "nodes": [
            {"data": {"title": "start", "type": "start", "variables": []}, "id": "start"},
            {"data": {"title": "answer", "type": "answer", "answer": "{{#node.response#}}"}, "id": "answer"},
            ContinueOnErrorTestHelper.get_http_node("default-value", {"response": "http node got error response"}),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(
        isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "http node got error response"}
        for e in events
    )
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_http_node_fail_branch_continue_on_error():
    """Test HTTP node with fail-branch error strategy"""
    graph_config = {
        "edges": FAIL_BRANCH_EDGES,
        "nodes": [
            {"data": {"title": "Start", "type": "start", "variables": []}, "id": "start"},
            {
                "data": {"title": "success", "type": "answer", "answer": "HTTP request successful"},
                "id": "success",
            },
            {
                "data": {"title": "error", "type": "answer", "answer": "HTTP request failed"},
                "id": "error",
            },
            ContinueOnErrorTestHelper.get_http_node(),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "HTTP request failed"} for e in events)
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_tool_node_default_value_continue_on_error():
    """Test tool node with default value error strategy"""
    graph_config = {
        "edges": DEFAULT_VALUE_EDGE,
        "nodes": [
            {"data": {"title": "start", "type": "start", "variables": []}, "id": "start"},
            {"data": {"title": "answer", "type": "answer", "answer": "{{#node.result#}}"}, "id": "answer"},
            ContinueOnErrorTestHelper.get_tool_node("default-value", {"result": "default tool result"}),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "default tool result"} for e in events)
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_tool_node_fail_branch_continue_on_error():
    """Test HTTP node with fail-branch error strategy"""
    graph_config = {
        "edges": FAIL_BRANCH_EDGES,
        "nodes": [
            {"data": {"title": "Start", "type": "start", "variables": []}, "id": "start"},
            {
                "data": {"title": "success", "type": "answer", "answer": "tool execute successful"},
                "id": "success",
            },
            {
                "data": {"title": "error", "type": "answer", "answer": "tool execute failed"},
                "id": "error",
            },
            ContinueOnErrorTestHelper.get_tool_node(),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "tool execute failed"} for e in events)
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_llm_node_default_value_continue_on_error():
    """Test LLM node with default value error strategy"""
    graph_config = {
        "edges": DEFAULT_VALUE_EDGE,
        "nodes": [
            {"data": {"title": "start", "type": "start", "variables": []}, "id": "start"},
            {"data": {"title": "answer", "type": "answer", "answer": "{{#node.answer#}}"}, "id": "answer"},
            ContinueOnErrorTestHelper.get_llm_node("default-value", {"answer": "default LLM response"}),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(
        isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "default LLM response"} for e in events
    )
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1


def test_llm_node_fail_branch_continue_on_error():
    """Test LLM node with fail-branch error strategy"""
    graph_config = {
        "edges": FAIL_BRANCH_EDGES,
        "nodes": [
            {"data": {"title": "Start", "type": "start", "variables": []}, "id": "start"},
            {
                "data": {"title": "success", "type": "answer", "answer": "LLM request successful"},
                "id": "success",
            },
            {
                "data": {"title": "error", "type": "answer", "answer": "LLM request failed"},
                "id": "error",
            },
            ContinueOnErrorTestHelper.get_llm_node(),
        ],
    }

    graph_engine = ContinueOnErrorTestHelper.create_test_graph_engine(graph_config)
    events = list(graph_engine.run())

    assert any(isinstance(e, NodeRunExceptionEvent) for e in events)
    assert any(isinstance(e, GraphRunSucceededEvent) and e.outputs == {"answer": "LLM request failed"} for e in events)
    assert sum(1 for e in events if isinstance(e, NodeRunStreamChunkEvent)) == 1