"""Label endpoint tests."""

import uuid
import pytest
from conftest import create_project, create_label


class TestCreateLabel:
    """Tests for POST /projects/{project_id}/labels"""
    
    def test_create_label_success(self, client):
        """Create a label with valid data."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/labels", json={
            "name": "bug",
            "color": "#ff0000"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "bug"
        assert data["color"] == "#ff0000"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_label_project_not_found(self, client):
        """Creating label in non-existent project returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/projects/{fake_id}/labels", json={
            "name": "bug",
            "color": "#ff0000"
        })
        assert resp.status_code == 404
    
    def test_create_label_duplicate_name(self, client):
        """Creating label with duplicate name returns 409."""
        project = create_project(client)
        create_label(client, project["id"], name="duplicate")
        resp = client.post(f"/projects/{project['id']}/labels", json={
            "name": "duplicate",
            "color": "#00ff00"
        })
        assert resp.status_code == 409
    
    def test_create_label_missing_name(self, client):
        """Creating label without name returns 400."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/labels", json={
            "color": "#ff0000"
        })
        assert resp.status_code == 400
    
    def test_create_label_missing_color(self, client):
        """Creating label without color returns 400."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/labels", json={
            "name": "test"
        })
        assert resp.status_code == 400
    
    def test_create_label_invalid_color(self, client):
        """Creating label with invalid color returns 400."""
        project = create_project(client)
        resp = client.post(f"/projects/{project['id']}/labels", json={
            "name": "test",
            "color": "red"  # Not hex format
        })
        assert resp.status_code == 400


class TestListLabels:
    """Tests for GET /projects/{project_id}/labels"""
    
    def test_list_labels_empty(self, client):
        """List labels in project with no labels."""
        project = create_project(client)
        resp = client.get(f"/projects/{project['id']}/labels")
        assert resp.status_code == 200
        data = resp.json()
        assert "labels" in data
        assert len(data["labels"]) == 0
    
    def test_list_labels_with_labels(self, client):
        """List labels in project with labels."""
        project = create_project(client)
        create_label(client, project["id"], name="bug", color="#ff0000")
        create_label(client, project["id"], name="feature", color="#00ff00")
        
        resp = client.get(f"/projects/{project['id']}/labels")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["labels"]) == 2
    
    def test_list_labels_project_not_found(self, client):
        """List labels in non-existent project returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/projects/{fake_id}/labels")
        assert resp.status_code == 404


class TestDeleteLabel:
    """Tests for DELETE /projects/{project_id}/labels/{label_id}"""
    
    def test_delete_label_success(self, client):
        """Delete an existing label."""
        project = create_project(client)
        label = create_label(client, project["id"])
        
        resp = client.delete(f"/projects/{project['id']}/labels/{label['id']}")
        assert resp.status_code == 204
    
    def test_delete_label_not_found(self, client):
        """Delete non-existent label returns 404."""
        project = create_project(client)
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/projects/{project['id']}/labels/{fake_id}")
        assert resp.status_code == 404
    
    def test_delete_label_removes_from_issues(self, client):
        """Deleting a label removes it from issues."""
        project = create_project(client)
        label = create_label(client, project["id"], name="removeme")
        
        # Create issue with label
        issue_resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Test issue",
            "labels": ["removeme"]
        })
        assert issue_resp.status_code == 201
        issue = issue_resp.json()
        assert "removeme" in issue["labels"]
        
        # Delete label
        client.delete(f"/projects/{project['id']}/labels/{label['id']}")
        
        # Issue should no longer have the label
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}")
        assert resp.status_code == 200
        assert "removeme" not in resp.json()["labels"]
