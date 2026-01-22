"""Integration tests for the complete workflow."""

import uuid
import pytest
from conftest import create_project, create_label, create_issue, create_comment


class TestCompleteWorkflow:
    """End-to-end workflow tests."""
    
    def test_full_issue_lifecycle(self, client):
        """Test complete issue lifecycle from creation to closure."""
        # 1. Create a project
        project = create_project(client, name=f"workflow-{uuid.uuid4().hex[:8]}")
        
        # 2. Create labels
        create_label(client, project["id"], name="bug", color="#ff0000")
        create_label(client, project["id"], name="urgent", color="#ff00ff")
        
        # 3. Create an issue with labels
        issue_resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Login page broken",
            "description": "Users can't log in with valid credentials",
            "priority": "high",
            "assignee": "alice",
            "labels": ["bug", "urgent"]
        })
        assert issue_resp.status_code == 201
        issue = issue_resp.json()
        assert issue["status"] == "open"
        
        # 4. Add a comment
        comment = create_comment(
            client, project["id"], issue["id"],
            author="alice", body="Investigating this now"
        )
        
        # 5. Update status to in_progress
        resp = client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={
            "status": "in_progress"
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"
        
        # 6. Add another comment
        create_comment(
            client, project["id"], issue["id"],
            author="alice", body="Found the root cause - session token validation"
        )
        
        # 7. Close the issue
        resp = client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={
            "status": "closed"
        })
        assert resp.status_code == 200
        closed_issue = resp.json()
        assert closed_issue["status"] == "closed"
        assert closed_issue["closed_at"] is not None
        
        # 8. Verify comments
        comments_resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}/comments")
        assert comments_resp.status_code == 200
        assert len(comments_resp.json()["comments"]) == 2
        
        # 9. List closed issues
        closed_resp = client.get(f"/projects/{project['id']}/issues", params={"status": "closed"})
        assert closed_resp.status_code == 200
        assert any(i["id"] == issue["id"] for i in closed_resp.json()["issues"])
    
    def test_search_across_issues(self, client):
        """Test searching across multiple issues."""
        project = create_project(client)
        
        # Create several issues
        create_issue(client, project["id"], title="Login bug", description="Authentication fails")
        create_issue(client, project["id"], title="Dashboard slow", description="Performance issue")
        create_issue(client, project["id"], title="API login endpoint", description="REST API")
        
        # Search for "login"
        resp = client.get(f"/projects/{project['id']}/issues", params={"search": "login"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2  # "Login bug" and "API login endpoint"
    
    def test_filter_by_multiple_criteria(self, client):
        """Test filtering with multiple criteria."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        
        # Create issues with various attributes
        issue1 = create_issue(client, project["id"], priority="high", labels=["bug"], assignee="alice")
        issue2 = create_issue(client, project["id"], priority="high", labels=["bug"], assignee="bob")
        issue3 = create_issue(client, project["id"], priority="low", labels=["bug"], assignee="alice")
        
        # Filter by priority=high AND assignee=alice
        resp = client.get(f"/projects/{project['id']}/issues", params={
            "priority": "high",
            "assignee": "alice"
        })
        assert resp.status_code == 200
        data = resp.json()
        for issue in data["issues"]:
            assert issue["priority"] == "high"
            assert issue["assignee"] == "alice"
    
    def test_cascade_delete_project(self, client):
        """Verify cascade delete removes all related data."""
        project = create_project(client)
        label = create_label(client, project["id"], name="test", color="#000000")
        issue = create_issue(client, project["id"], labels=["test"])
        comment = create_comment(client, project["id"], issue["id"])
        
        # Delete project
        resp = client.delete(f"/projects/{project['id']}")
        assert resp.status_code == 204
        
        # All should be gone
        assert client.get(f"/projects/{project['id']}").status_code == 404
        assert client.get(f"/projects/{project['id']}/labels").status_code == 404
        assert client.get(f"/projects/{project['id']}/issues/{issue['id']}").status_code == 404
    
    def test_concurrent_label_operations(self, client):
        """Test label add/remove operations don't corrupt data."""
        project = create_project(client)
        create_label(client, project["id"], name="label1", color="#111111")
        create_label(client, project["id"], name="label2", color="#222222")
        create_label(client, project["id"], name="label3", color="#333333")
        
        issue = create_issue(client, project["id"])
        
        # Add labels
        client.post(f"/projects/{project['id']}/issues/{issue['id']}/labels", json={"name": "label1"})
        client.post(f"/projects/{project['id']}/issues/{issue['id']}/labels", json={"name": "label2"})
        client.post(f"/projects/{project['id']}/issues/{issue['id']}/labels", json={"name": "label3"})
        
        # Remove one
        client.delete(f"/projects/{project['id']}/issues/{issue['id']}/labels/label2")
        
        # Verify final state
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}")
        labels = set(resp.json()["labels"])
        assert labels == {"label1", "label3"}
