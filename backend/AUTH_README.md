# Authentication System Setup

This guide explains how to set up and use the user authentication system with Alembic migrations.

## 🚀 Quick Setup

### 1. Environment Variables

Copy the environment template and fill in your values:

```bash
cp ENV.template .env
```

Update `.env` with your actual values:

```env
# Authentication variables
SECRET_KEY="your-super-secret-jwt-key-here-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES="30"

# Database configuration
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/resume_parser"
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

### 3. Database Setup

Make sure PostgreSQL is running, then:

```bash
# Create the initial migration
alembic revision --autogenerate -m "Create user table"

# Apply the migration
alembic upgrade head
```

### 4. Start the Server

```bash
# Development mode
uvicorn src.agent.app:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/auth/register` | POST | Register new user | No |
| `/auth/login` | POST | Login user | No |
| `/auth/me` | GET | Get current user info | Yes |
| `/auth/protected` | GET | Example protected route | Yes |

### Example Usage

#### Register a new user

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "securepassword123",
    "full_name": "Test User"
  }'
```

#### Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

This returns a JWT token:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "email": "user@example.com",
    "username": "testuser",
    "full_name": "Test User",
    "id": 1,
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Access protected routes

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE"
```

## 🏗️ Database Models

### User Model

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

## 🔐 Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Email/Username Uniqueness**: Prevents duplicate accounts
- **Account Status**: Active/inactive and verified/unverified states
- **CORS Support**: Configured for frontend development

## 🔧 Database Migrations

### Create a new migration

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply to specific revision
alembic upgrade revision_id

# Rollback one migration
alembic downgrade -1
```

### View migration history

```bash
alembic history
alembic current
```

## 🧪 Testing the Authentication

You can test the authentication system using the interactive API docs:

1. Start the server: `uvicorn src.agent.app:app --reload`
2. Open http://localhost:8000/docs
3. Register a new user via `/auth/register`
4. Login via `/auth/login` to get a token
5. Click "Authorize" and enter: `Bearer YOUR_TOKEN`
6. Test protected endpoints

## 🔒 Security Considerations for Production

1. **Change the SECRET_KEY**: Use a strong, random secret key
2. **Use HTTPS**: Always use SSL/TLS in production
3. **Database Security**: Use strong passwords and restrict access
4. **Token Expiration**: Consider shorter expiration times for sensitive apps
5. **Rate Limiting**: Implement rate limiting for auth endpoints
6. **Input Validation**: All inputs are validated using Pydantic schemas
7. **Environment Variables**: Never commit sensitive data to version control

## 📁 File Structure

```
backend/
├── src/agent/
│   ├── database.py      # Database configuration
│   ├── models.py        # SQLAlchemy models
│   ├── auth.py          # Authentication utilities
│   ├── schemas.py       # Pydantic schemas
│   ├── user_service.py  # User business logic
│   └── app.py           # FastAPI application with auth routes
├── alembic/             # Database migrations
│   ├── env.py           # Alembic environment config
│   └── versions/        # Migration files
├── alembic.ini          # Alembic configuration
├── ENV.template         # Environment variables template
└── setup_auth_db.py     # Database setup script
```