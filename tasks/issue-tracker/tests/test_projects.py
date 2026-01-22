"""Project endpoint tests."""

import uuid
import pytest
from conftest import create_project


class TestCreateProject:
    """Tests for POST /projects"""
    
    def test_create_project_success(self, client):
        """Create a project with valid data."""
        name = f"test-project-{uuid.uuid4().hex[:8]}"
        resp = client.post("/projects", json={
            "name": name,
            "description": "A test project"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == name
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_project_minimal(self, client):
        """Create a project with only required fields."""
        name = f"minimal-{uuid.uuid4().hex[:8]}"
        resp = client.post("/projects", json={"name": name})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == name
    
    def test_create_project_missing_name(self, client):
        """Creating a project without name should fail."""
        resp = client.post("/projects", json={"description": "No name"})
        assert resp.status_code == 400
    
    def test_create_project_empty_name(self, client):
        """Creating a project with empty name should fail."""
        resp = client.post("/projects", json={"name": ""})
        assert resp.status_code == 400
    
    def test_create_project_whitespace_name(self, client):
        """Creating a project with whitespace-only name should fail."""
        resp = client.post("/projects", json={"name": "   "})
        assert resp.status_code == 400
    
    def test_create_project_duplicate_name(self, client):
        """Creating a project with duplicate name should fail."""
        name = f"duplicate-{uuid.uuid4().hex[:8]}"
        client.post("/projects", json={"name": name})
        resp = client.post("/projects", json={"name": name})
        assert resp.status_code == 409
    
    def test_create_project_name_too_long(self, client):
        """Creating a project with name > 100 chars should fail."""
        resp = client.post("/projects", json={"name": "x" * 101})
        assert resp.status_code == 400


class TestListProjects:
    """Tests for GET /projects"""
    
    def test_list_projects_empty(self, client):
        """List projects returns proper structure."""
        resp = client.get("/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
    
    def test_list_projects_pagination(self, client):
        """Pagination works correctly."""
        # Create a few projects
        for i in range(3):
            create_project(client, name=f"paginate-{uuid.uuid4().hex[:8]}")
        
        resp = client.get("/projects", params={"limit": 2, "offset": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["projects"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0
    
    def test_list_projects_limit_cap(self, client):
        """Limit is capped at 100."""
        resp = client.get("/projects", params={"limit": 200})
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] <= 100


class TestGetProject:
    """Tests for GET /projects/{project_id}"""
    
    def test_get_project_success(self, client):
        """Get an existing project."""
        project = create_project(client)
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == project["id"]
        assert data["name"] == project["name"]
    
    def test_get_project_not_found(self, client):
        """Getting a non-existent project returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/projects/{fake_id}")
        assert resp.status_code == 404


class TestUpdateProject:
    """Tests for PATCH /projects/{project_id}"""
    
    def test_update_project_name(self, client):
        """Update project name."""
        project = create_project(client)
        new_name = f"updated-{uuid.uuid4().hex[:8]}"
        resp = client.patch(f"/projects/{project['id']}", json={"name": new_name})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == new_name
    
    def test_update_project_description(self, client):
        """Update project description."""
        project = create_project(client)
        resp = client.patch(f"/projects/{project['id']}", json={"description": "New desc"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "New desc"
    
    def test_update_project_not_found(self, client):
        """Updating a non-existent project returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.patch(f"/projects/{fake_id}", json={"name": "test"})
        assert resp.status_code == 404
    
    def test_update_project_duplicate_name(self, client):
        """Updating to a duplicate name returns 409."""
        project1 = create_project(client)
        project2 = create_project(client)
        resp = client.patch(f"/projects/{project2['id']}", json={"name": project1["name"]})
        assert resp.status_code == 409


class TestDeleteProject:
    """Tests for DELETE /projects/{project_id}"""
    
    def test_delete_project_success(self, client):
        """Delete an existing project."""
        project = create_project(client)
        resp = client.delete(f"/projects/{project['id']}")
        assert resp.status_code == 204
        
        # Verify it's gone
        resp = client.get(f"/projects/{project['id']}")
        assert resp.status_code == 404
    
    def test_delete_project_not_found(self, client):
        """Deleting a non-existent project returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/projects/{fake_id}")
        assert resp.status_code == 404
    
    def test_delete_project_cascades(self, client):
        """Deleting a project deletes its issues and labels."""
        project = create_project(client)
        
        # Create a label
        label_resp = client.post(f"/projects/{project['id']}/labels", json={
            "name": "test-label",
            "color": "#ff0000"
        })
        assert label_resp.status_code == 201
        
        # Create an issue
        issue_resp = client.post(f"/projects/{project['id']}/issues", json={
            "title": "Test issue"
        })
        assert issue_resp.status_code == 201
        issue = issue_resp.json()
        
        # Delete project
        resp = client.delete(f"/projects/{project['id']}")
        assert resp.status_code == 204
        
        # Issue should be gone too
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}")
        assert resp.status_code == 404
