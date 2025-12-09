---
name: backend-api
description: Backend API development practices
version: 1.0
author: ReACTOR Team
allowed_tools:
  - read_file_content
  - write_file
  - modify_file
  - search_in_files
  - execute_shell_command
working_patterns:
  - "**/api/**/*.py"
  - "**/routes/**/*.py"
  - "**/models/**/*.py"
---

# Backend API Development Skill

## Architecture Principles

### RESTful Design
- Use proper HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Consistent URL structure (`/api/v1/resource`)
- Proper HTTP status codes
- API versioning in URLs

### Request/Response Format
```python
# Request validation
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# Response structure
{
  "success": true,
  "data": {...},
  "error": null
}
```

## Security

### Essential Practices
- Input validation on all endpoints
- Authentication/Authorization (JWT, OAuth)
- Rate limiting to prevent abuse
- CORS configuration
- SQL injection prevention (use ORMs)
- XSS protection

### Example
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/api/v1/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"message": "Access granted"}
```

## Error Handling

### Consistent Error Format
```python
class APIError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

@app.exception_handler(APIError)
async def api_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": false,
            "error": {
                "code": exc.status_code,
                "message": exc.detail
            }
        }
    )
```

## Testing

### API Testing
- Unit tests for business logic
- Integration tests for endpoints
- Test authentication/authorization
- Test error handling

### Example
```python
def test_create_user():
    response = client.post("/api/v1/users", json={
        "username": "test",
        "email": "test@example.com",
        "password": "secure123"
    })
    assert response.status_code == 201
    assert "id" in response.json()["data"]
```
