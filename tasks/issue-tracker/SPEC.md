# Mini Issue Tracker API Specification

Build a REST API for a simple issue tracking system. This system manages projects, issues, comments, and labels.

## Data Models

### Project
```json
{
  "id": "string (UUID)",
  "name": "string (1-100 chars, unique)",
  "description": "string (0-1000 chars)",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

### Issue
```json
{
  "id": "string (UUID)",
  "project_id": "string (UUID, required)",
  "title": "string (1-200 chars)",
  "description": "string (0-5000 chars)",
  "status": "string (open|in_progress|closed)",
  "priority": "string (low|medium|high|critical)",
  "assignee": "string or null (0-100 chars)",
  "labels": ["array of label names"],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "closed_at": "ISO8601 datetime or null"
}
```

### Comment
```json
{
  "id": "string (UUID)",
  "issue_id": "string (UUID)",
  "author": "string (1-100 chars)",
  "body": "string (1-5000 chars)",
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime"
}
```

### Label
```json
{
  "id": "string (UUID)",
  "project_id": "string (UUID)",
  "name": "string (1-50 chars, unique per project)",
  "color": "string (hex color, e.g., #ff0000)",
  "created_at": "ISO8601 datetime"
}
```

---

## API Endpoints

### Health Check

#### GET /healthz
Returns service health status.

**Response 200:**
```json
{"status": "ok"}
```

---

### Projects

#### POST /projects
Create a new project.

**Request Body:**
```json
{
  "name": "My Project",
  "description": "Optional description"
}
```

**Response 201:** Returns the created project.

**Response 400:** Invalid input (missing name, name too long, etc.)

**Response 409:** Project with this name already exists.

---

#### GET /projects
List all projects.

**Query Parameters:**
- `limit` (optional, default 20, max 100)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "projects": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

#### GET /projects/{project_id}
Get a project by ID.

**Response 200:** Returns the project.

**Response 404:** Project not found.

---

#### PATCH /projects/{project_id}
Update a project.

**Request Body:** (all fields optional)
```json
{
  "name": "New Name",
  "description": "New description"
}
```

**Response 200:** Returns the updated project.

**Response 400:** Invalid input.

**Response 404:** Project not found.

**Response 409:** Name conflicts with existing project.

---

#### DELETE /projects/{project_id}
Delete a project and all its issues, comments, and labels.

**Response 204:** Successfully deleted.

**Response 404:** Project not found.

---

### Labels

#### POST /projects/{project_id}/labels
Create a label in a project.

**Request Body:**
```json
{
  "name": "bug",
  "color": "#ff0000"
}
```

**Response 201:** Returns the created label.

**Response 400:** Invalid input.

**Response 404:** Project not found.

**Response 409:** Label with this name already exists in project.

---

#### GET /projects/{project_id}/labels
List all labels in a project.

**Response 200:**
```json
{
  "labels": [...]
}
```

**Response 404:** Project not found.

---

#### DELETE /projects/{project_id}/labels/{label_id}
Delete a label. Removes the label from all issues.

**Response 204:** Successfully deleted.

**Response 404:** Project or label not found.

---

### Issues

#### POST /projects/{project_id}/issues
Create an issue.

**Request Body:**
```json
{
  "title": "Something is broken",
  "description": "Detailed description...",
  "priority": "high",
  "assignee": "alice",
  "labels": ["bug", "urgent"]
}
```

**Defaults:**
- `status`: "open"
- `priority`: "medium" if not provided
- `labels`: [] if not provided

**Response 201:** Returns the created issue.

**Response 400:** Invalid input (missing title, invalid priority, label doesn't exist, etc.)

**Response 404:** Project not found.

---

#### GET /projects/{project_id}/issues
List issues in a project with filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by status (open, in_progress, closed)
- `priority` (optional): Filter by priority (low, medium, high, critical)
- `assignee` (optional): Filter by assignee
- `label` (optional): Filter by label name (can specify multiple)
- `search` (optional): Search in title and description (case-insensitive substring match)
- `sort` (optional): Sort field (created_at, updated_at, priority). Default: created_at
- `order` (optional): Sort order (asc, desc). Default: desc
- `limit` (optional, default 20, max 100)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "issues": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

**Response 404:** Project not found.

---

#### GET /projects/{project_id}/issues/{issue_id}
Get an issue by ID.

**Response 200:** Returns the issue.

**Response 404:** Project or issue not found.

---

#### PATCH /projects/{project_id}/issues/{issue_id}
Update an issue.

**Request Body:** (all fields optional)
```json
{
  "title": "Updated title",
  "description": "Updated description",
  "status": "in_progress",
  "priority": "critical",
  "assignee": "bob"
}
```

**Special Behavior:**
- When `status` changes to "closed", set `closed_at` to current time
- When `status` changes from "closed" to something else, set `closed_at` to null
- Always update `updated_at`

**Response 200:** Returns the updated issue.

**Response 400:** Invalid input.

**Response 404:** Project or issue not found.

---

#### DELETE /projects/{project_id}/issues/{issue_id}
Delete an issue and all its comments.

**Response 204:** Successfully deleted.

**Response 404:** Project or issue not found.

---

### Issue Labels

#### POST /projects/{project_id}/issues/{issue_id}/labels
Add a label to an issue.

**Request Body:**
```json
{
  "name": "bug"
}
```

**Response 200:** Returns the updated issue.

**Response 400:** Invalid input.

**Response 404:** Project, issue, or label not found.

**Response 409:** Label already attached to issue (idempotent: treat as success, return 200).

---

#### DELETE /projects/{project_id}/issues/{issue_id}/labels/{label_name}
Remove a label from an issue.

**Response 200:** Returns the updated issue.

**Response 404:** Project, issue, or label not found on issue.

---

### Comments

#### POST /projects/{project_id}/issues/{issue_id}/comments
Add a comment to an issue.

**Request Body:**
```json
{
  "author": "alice",
  "body": "This is my comment..."
}
```

**Response 201:** Returns the created comment.

**Response 400:** Invalid input.

**Response 404:** Project or issue not found.

---

#### GET /projects/{project_id}/issues/{issue_id}/comments
List comments on an issue.

**Query Parameters:**
- `limit` (optional, default 20, max 100)
- `offset` (optional, default 0)

**Response 200:**
```json
{
  "comments": [...],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

**Response 404:** Project or issue not found.

---

#### PATCH /projects/{project_id}/issues/{issue_id}/comments/{comment_id}
Update a comment.

**Request Body:**
```json
{
  "body": "Updated comment text"
}
```

**Response 200:** Returns the updated comment.

**Response 400:** Invalid input.

**Response 404:** Project, issue, or comment not found.

---

#### DELETE /projects/{project_id}/issues/{issue_id}/comments/{comment_id}
Delete a comment.

**Response 204:** Successfully deleted.

**Response 404:** Project, issue, or comment not found.

---

## Business Rules

1. **Unique Constraints:**
   - Project names must be unique (case-sensitive)
   - Label names must be unique within a project (case-sensitive)

2. **Cascading Deletes:**
   - Deleting a project deletes all its labels, issues, and comments
   - Deleting an issue deletes all its comments
   - Deleting a label removes it from all issues

3. **Status Transitions:**
   - Issues can transition between any statuses
   - `closed_at` is set when status becomes "closed"
   - `closed_at` is cleared when status changes from "closed" to anything else

4. **Label Validation:**
   - When creating/updating an issue with labels, all labels must exist in the project
   - Adding a label that's already on an issue is idempotent (success, no duplicate)

5. **Priority Ordering:**
   - When sorting by priority: critical > high > medium > low

6. **Timestamps:**
   - `created_at` is set on creation and never changes
   - `updated_at` is set on creation and updated on any modification

7. **Pagination:**
   - Must return accurate `total` count for the current filter
   - `limit` capped at 100
   - Results should be stable (consistent ordering)

---

## Validation Rules

- All string fields should be trimmed of leading/trailing whitespace
- Empty strings after trimming should be treated as missing (for required fields)
- UUIDs should be validated format
- Colors must be valid hex format: `#RRGGBB` (6 hex digits after #)
- Priorities must be one of: low, medium, high, critical
- Statuses must be one of: open, in_progress, closed

---

## Performance Expectations

- All endpoints should respond within 500ms
- Pagination should be efficient (not load all data for counting)
- Filtering should be reasonably efficient

---

## Example Workflow

1. Create a project "Backend API"
2. Create labels: "bug" (red), "feature" (green), "docs" (blue)
3. Create an issue: "Fix login bug", priority high, label "bug"
4. Add a comment: "Investigating this now"
5. Update issue status to "in_progress"
6. Add another comment: "Found the root cause"
7. Update issue status to "closed"
8. List all closed issues
9. Search for issues containing "login"
