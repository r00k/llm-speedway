"""Comment endpoint tests."""

import uuid
import pytest
from conftest import create_project, create_issue, create_comment


class TestCreateComment:
    """Tests for POST /projects/{project_id}/issues/{issue_id}/comments"""
    
    def test_create_comment_success(self, client):
        """Create a comment with valid data."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.post(f"/projects/{project['id']}/issues/{issue['id']}/comments", json={
            "author": "alice",
            "body": "This is a comment"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["author"] == "alice"
        assert data["body"] == "This is a comment"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_comment_missing_author(self, client):
        """Creating comment without author returns 400."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.post(f"/projects/{project['id']}/issues/{issue['id']}/comments", json={
            "body": "No author"
        })
        assert resp.status_code == 400
    
    def test_create_comment_missing_body(self, client):
        """Creating comment without body returns 400."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.post(f"/projects/{project['id']}/issues/{issue['id']}/comments", json={
            "author": "alice"
        })
        assert resp.status_code == 400
    
    def test_create_comment_issue_not_found(self, client):
        """Creating comment on non-existent issue returns 404."""
        project = create_project(client)
        fake_id = str(uuid.uuid4())
        
        resp = client.post(f"/projects/{project['id']}/issues/{fake_id}/comments", json={
            "author": "alice",
            "body": "Comment"
        })
        assert resp.status_code == 404


class TestListComments:
    """Tests for GET /projects/{project_id}/issues/{issue_id}/comments"""
    
    def test_list_comments_empty(self, client):
        """List comments on issue with no comments."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert "comments" in data
        assert len(data["comments"]) == 0
    
    def test_list_comments_with_comments(self, client):
        """List comments on issue with comments."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        create_comment(client, project["id"], issue["id"], body="Comment 1")
        create_comment(client, project["id"], issue["id"], body="Comment 2")
        
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["comments"]) == 2
    
    def test_list_comments_pagination(self, client):
        """Pagination works correctly."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        for i in range(5):
            create_comment(client, project["id"], issue["id"])
        
        resp = client.get(f"/projects/{project['id']}/issues/{issue['id']}/comments", params={"limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["comments"]) == 2
        assert data["total"] >= 5


class TestUpdateComment:
    """Tests for PATCH /projects/{project_id}/issues/{issue_id}/comments/{comment_id}"""
    
    def test_update_comment_success(self, client):
        """Update a comment."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        comment = create_comment(client, project["id"], issue["id"])
        
        resp = client.patch(
            f"/projects/{project['id']}/issues/{issue['id']}/comments/{comment['id']}",
            json={"body": "Updated body"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["body"] == "Updated body"
    
    def test_update_comment_not_found(self, client):
        """Update non-existent comment returns 404."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        fake_id = str(uuid.uuid4())
        
        resp = client.patch(
            f"/projects/{project['id']}/issues/{issue['id']}/comments/{fake_id}",
            json={"body": "Updated"}
        )
        assert resp.status_code == 404


class TestDeleteComment:
    """Tests for DELETE /projects/{project_id}/issues/{issue_id}/comments/{comment_id}"""
    
    def test_delete_comment_success(self, client):
        """Delete a comment."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        comment = create_comment(client, project["id"], issue["id"])
        
        resp = client.delete(f"/projects/{project['id']}/issues/{issue['id']}/comments/{comment['id']}")
        assert resp.status_code == 204
    
    def test_delete_comment_not_found(self, client):
        """Delete non-existent comment returns 404."""
        project = create_project(client)
        issue = create_issue(client, project["id"])
        fake_id = str(uuid.uuid4())
        
        resp = client.delete(f"/projects/{project['id']}/issues/{issue['id']}/comments/{fake_id}")
        assert resp.status_code == 404
