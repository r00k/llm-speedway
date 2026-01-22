"""Issue label management tests."""

import uuid
import pytest
from conftest import create_project, create_label, create_issue


class TestAddLabelToIssue:
    """Tests for POST /projects/{project_id}/issues/{issue_id}/labels"""
    
    def test_add_label_success(self, client):
        """Add a label to an issue."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        issue = create_issue(client, project["id"])
        
        resp = client.post(f"/projects/{project['id']}/issues/{issue['id']}/labels", json={
            "name": "bug"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "bug" in data["labels"]
    
    def test_add_label_idempotent(self, client):
        """Adding the same label twice is idempotent."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        issue = create_issue(client, project["id"], labels=["bug"])
        
        # Add it again
        resp = client.post(f"/projects/{project['id']}/issues/{issue['id']}/labels", json={
            "name": "bug"
        })
        # Should succeed (idempotent)
        assert resp.status_code in [200, 409]
        if resp.status_code == 200:
            data = resp.json()
            assert data["labels"].count("bug") == 1  # No duplicate
    
    def test_add_label_not_found(self, client):
        """Adding a non-existent label returns 404."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.post(f"/projects/{project['id']}/issues/{issue['id']}/labels", json={
            "name": "nonexistent"
        })
        assert resp.status_code == 404


class TestRemoveLabelFromIssue:
    """Tests for DELETE /projects/{project_id}/issues/{issue_id}/labels/{label_name}"""
    
    def test_remove_label_success(self, client):
        """Remove a label from an issue."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        issue = create_issue(client, project["id"], labels=["bug"])
        
        resp = client.delete(f"/projects/{project['id']}/issues/{issue['id']}/labels/bug")
        assert resp.status_code == 200
        data = resp.json()
        assert "bug" not in data["labels"]
    
    def test_remove_label_not_on_issue(self, client):
        """Removing a label not on the issue returns 404."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        issue = create_issue(client, project["id"])  # No labels
        
        resp = client.delete(f"/projects/{project['id']}/issues/{issue['id']}/labels/bug")
        assert resp.status_code == 404
