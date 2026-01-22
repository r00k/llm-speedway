"""Issue endpoint tests."""

import uuid
import pytest
from conftest import create_project, create_label, create_issue


class TestCreateIssue:
    """Tests for POST /projects/{project_id}/issues"""
    
    def test_create_issue_success(self, client):
        """Create an issue with valid data."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Something is broken",
            "description": "It doesn't work",
            "priority": "high"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Something is broken"
        assert data["description"] == "It doesn't work"
        assert data["priority"] == "high"
        assert data["status"] == "open"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["closed_at"] is None
    
    def test_create_issue_minimal(self, client):
        """Create an issue with only title."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Minimal issue"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Minimal issue"
        assert data["status"] == "open"
        assert data["priority"] == "medium"  # Default
    
    def test_create_issue_with_labels(self, client):
        """Create an issue with labels."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        create_label(client, project["id"], name="urgent", color="#ff00ff")
        
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Labeled issue",
            "labels": ["bug", "urgent"]
        })
        assert resp.status_code == 201
        data = resp.json()
        assert set(data["labels"]) == {"bug", "urgent"}
    
    def test_create_issue_with_assignee(self, client):
        """Create an issue with assignee."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Assigned issue",
            "assignee": "alice"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["assignee"] == "alice"
    
    def test_create_issue_missing_title(self, client):
        """Creating issue without title returns 400."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "description": "No title"
        })
        assert resp.status_code == 400
    
    def test_create_issue_invalid_priority(self, client):
        """Creating issue with invalid priority returns 400."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Test",
            "priority": "super-urgent"
        })
        assert resp.status_code == 400
    
    def test_create_issue_nonexistent_label(self, client):
        """Creating issue with non-existent label returns 400."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Test",
            "labels": ["nonexistent"]
        })
        assert resp.status_code == 400
    
    def test_create_issue_project_not_found(self, client):
        """Creating issue in non-existent project returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/projects/{fake_id}/issues", json={
            "title": "Test"
        })
        assert resp.status_code == 404


class TestListIssues:
    """Tests for GET /projects/{project_id}/issues"""
    
    def test_list_issues_empty(self, client):
        """List issues in project with no issues."""
        project = create_project(client)
        resp = client.get(f"/projects/{project['id']}/issues")
        assert resp.status_code == 200
        data = resp.json()
        assert "issues" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
    
    def test_list_issues_with_issues(self, client):
        """List issues in project with issues."""
        project = create_project(client)
        create_issue(client, project["id"], title="Issue 1")
        create_issue(client, project["id"], title="Issue 2")
        
        resp = client.get(f"/projects/{project['id']}/issues")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
    
    def test_list_issues_filter_status(self, client):
        """Filter issues by status."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={"status": "closed"})
        create_issue(client, project["id"])  # open
        
        resp = client.get(f"/projects/{project['id']}/issues", params={"status": "closed"})
        assert resp.status_code == 200
        data = resp.json()
        for issue in data["issues"]:
            assert issue["status"] == "closed"
    
    def test_list_issues_filter_priority(self, client):
        """Filter issues by priority."""
        project = create_project(client)
        create_issue(client, project["id"], priority="high")
        create_issue(client, project["id"], priority="low")
        
        resp = client.get(f"/projects/{project['id']}/issues", params={"priority": "high"})
        assert resp.status_code == 200
        data = resp.json()
        for issue in data["issues"]:
            assert issue["priority"] == "high"
    
    def test_list_issues_filter_assignee(self, client):
        """Filter issues by assignee."""
        project = create_project(client)
        create_issue(client, project["id"], assignee="alice")
        create_issue(client, project["id"], assignee="bob")
        
        resp = client.get(f"/projects/{project['id']}/issues", params={"assignee": "alice"})
        assert resp.status_code == 200
        data = resp.json()
        for issue in data["issues"]:
            assert issue["assignee"] == "alice"
    
    def test_list_issues_filter_label(self, client):
        """Filter issues by label."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        create_label(client, project["id"], name="feature", color="#00ff00")
        create_issue(client, project["id"], labels=["bug"])
        create_issue(client, project["id"], labels=["feature"])
        
        resp = client.get(f"/projects/{project['id']}/issues", params={"label": "bug"})
        assert resp.status_code == 200
        data = resp.json()
        for issue in data["issues"]:
            assert "bug" in issue["labels"]
    
    def test_list_issues_search(self, client):
        """Search issues by text."""
        project = create_project(client)
        create_issue(client, project["id"], title="Login bug", description="Can't log in")
        create_issue(client, project["id"], title="Other issue")
        
        resp = client.get(f"/projects/{project['id']}/issues", params={"search": "login"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        # All results should contain "login" in title or description
        for issue in data["issues"]:
            assert "login" in issue["title"].lower() or "login" in (issue.get("description") or "").lower()
    
    def test_list_issues_pagination(self, client):
        """Pagination works correctly."""
        project = create_project(client)
        for i in range(5):
            create_issue(client, project["id"])
        
        resp = client.get(f"/projects/{project['id']}/issues", params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["issues"]) == 2
        assert data["total"] >= 5


class TestGetIssue:
    """Tests for GET /projects/{project_id}/issues/{issue_id}"""
    
    def test_get_issue_success(self, client):
        """Get an existing issue."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == issue["id"]
    
    def test_get_issue_not_found(self, client):
        """Get non-existent issue returns 404."""
        project = create_project(client)
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/projects/{project['id']}/issues/{fake_id}")
        assert resp.status_code == 404


class TestUpdateIssue:
    """Tests for PATCH /projects/{project_id}/issues/{issue_id}"""
    
    def test_update_issue_title(self, client):
        """Update issue title."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={
            "title": "Updated title"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated title"
    
    def test_update_issue_status_to_closed(self, client):
        """Closing an issue sets closed_at."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={
            "status": "closed"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "closed"
        assert data["closed_at"] is not None
    
    def test_update_issue_reopen(self, client):
        """Reopening an issue clears closed_at."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        # Close it
        client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={"status": "closed"})
        
        # Reopen it
        resp = client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={
            "status": "open"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "open"
        assert data["closed_at"] is None
    
    def test_update_issue_updated_at_changes(self, client):
        """Updating an issue changes updated_at."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        original_updated = issue["updated_at"]
        
        import time
        time.sleep(0.1)  # Ensure time difference
        
        resp = client.patch(f"/projects/{project['id']}/issues/{issue['id']}", json={
            "title": "Changed"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_at"] != original_updated


class TestDeleteIssue:
    """Tests for DELETE /projects/{project_id}/issues/{issue_id}"""
    
    def test_delete_issue_success(self, client):
        """Delete an existing issue."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.delete(f"/projects/{project['id']}/issues/{issue['id']}")
        assert resp.status_code == 204
        
        # Verify it's gone
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}")
        assert resp.status_code == 404
    
    def test_delete_issue_not_found(self, client):
        """Delete non-existent issue returns 404."""
        project = create_project(client)
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/projects/{project['id']}/issues/{fake_id}")
        assert resp.status_code == 404
