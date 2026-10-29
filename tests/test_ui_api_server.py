import pytest
from starlette.testclient import TestClient
from app.api_server import api_app

@pytest.fixture
def client():
    return TestClient(api_app)

def test_api_status_endpoint(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "connected"
    assert "gemini_model" in data
    assert "vault_stats" in data
    assert isinstance(data["max_calls"], int)

def test_api_conversations_and_messages(client):
    # Create conversation
    res = client.post("/api/conversations", json={"title": "Test UI Session", "project_id": "test-proj"})
    assert res.status_code == 200
    conv_id = res.json()["conversation_id"]

    # List conversations
    res_list = client.get("/api/conversations?project_id=test-proj")
    assert res_list.status_code == 200
    assert any(c["id"] == conv_id for c in res_list.json()["conversations"])

    # Get messages
    res_msgs = client.get(f"/api/messages?conversation_id={conv_id}")
    assert res_msgs.status_code == 200
    assert isinstance(res_msgs.json()["messages"], list)

def test_api_agents_endpoint(client):
    res = client.get("/api/agents")
    assert res.status_code == 200
    data = res.json()
    assert "roles" in data
    # Exactly 7 logical specialist roles
    roles = data["roles"]
    assert len(roles) == 7
    role_names = [r["role"] for r in roles]
    assert "planner" in role_names
    assert "developer" in role_names
    assert "tester" in role_names
    assert "reviewer" in role_names
    assert "researcher" in role_names
    assert "learning_agent" in role_names
    assert "memory_manager" in role_names

def test_api_knowledge_graph_endpoint(client):
    res = client.get("/api/graph?project_id=default")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert data["total_nodes"] >= 8  # Project node + 7 agent nodes + any memories
    # Ensure Cytoscape compatible data format: node['data']['id']
    for n in data["nodes"]:
        assert "data" in n
        assert "id" in n["data"]
        assert "kind" in n["data"]
    for e in data["edges"]:
        assert "data" in e
        assert "source" in e["data"]
        assert "target" in e["data"]
        assert "label" in e["data"]

def test_api_memory_endpoint(client):
    res = client.get("/api/memory")
    assert res.status_code == 200
    data = res.json()
    assert "approved" in data
    assert "pending" in data
    assert "conflicts" in data
    assert "archived" in data

def test_api_memory_health_endpoint(client):
    res = client.get("/api/memory/health")
    assert res.status_code == 200
    data = res.json()
    assert "approved_notes_count" in data
    assert "findings" in data
    assert isinstance(data["findings"], list)

def test_api_automations_endpoint(client):
    res = client.get("/api/automations")
    assert res.status_code == 200
    data = res.json()
    assert "connected" in data
    # Truthful status: false when not configured
    assert data["connected"] is False
    assert "No automations connected" in data["message"]

def test_api_chat_endpoint(client):
    res = client.post("/api/chat", json={
        "task": "What is 2 + 2?",
        "project_id": "default",
        "conversation_id": "test-chat-conv",
        "collaborative": False,
        "allow_revise": False,
        "mock": True
    })
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert "status" in data
    assert "verdict" in data
    assert "result" in data
    assert "steps" in data
    assert len(data["steps"]) > 0
    step_agents = [s["agent"] for s in data["steps"]]
    assert "planner" in step_agents
    assert "developer" in step_agents

def test_api_settings_endpoint(client):
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "gemini_model" in data
    assert "vault_name" in data
    # Never expose API key string
    assert "api_key" not in data
    assert "has_api_key" in data
