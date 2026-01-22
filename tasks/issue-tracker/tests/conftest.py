"""Pytest configuration and fixtures for issue tracker tests."""

import os
import pytest
import httpx

BASE_URL = os.environ.get("SERVICE_URL", os.environ.get("BASE_URL", "http://127.0.0.1:8080"))


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for the service."""
    return BASE_URL


@pytest.fixture(scope="session")
def client(base_url):
    """Create an HTTP client for the service."""
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def fresh_client(base_url):
    """Create a fresh HTTP client (for tests that need isolation)."""
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client


def create_project(client, name=None, description="Test project"):
    """Helper to create a project."""
    import uuid
    name = name or f"project-{uuid.uuid4().hex[:8]}"
    resp = client.post("/projects", json={"name": name, "description": description})
    assert resp.status_code == 201, f"Failed to create project: {resp.text}"
    return resp.json()


def create_label(client, project_id, name=None, color="#ff0000"):
    """Helper to create a label."""
    import uuid
    name = name or f"label-{uuid.uuid4().hex[:8]}"
    resp = client.post(f"/projects/{project_id}/labels", json={"name": name, "color": color})
    assert resp.status_code == 201, f"Failed to create label: {resp.text}"
    return resp.json()


def create_issue(client, project_id, title=None, **kwargs):
    """Helper to create an issue."""
    import uuid
    title = title or f"Issue {uuid.uuid4().hex[:8]}"
    data = {"title": title, **kwargs}
    resp = client.post(f"/projects/{project_id}/issues", json=data)
    assert resp.status_code == 201, f"Failed to create issue: {resp.text}"
    return resp.json()


def create_comment(client, project_id, issue_id, author="tester", body=None):
    """Helper to create a comment."""
    import uuid
    body = body or f"Comment {uuid.uuid4().hex[:8]}"
    resp = client.post(
        f"/projects/{project_id}/issues/{issue_id}/comments",
        json={"author": author, "body": body}
    )
    assert resp.status_code == 201, f"Failed to create comment: {resp.text}"
    return resp.json()
