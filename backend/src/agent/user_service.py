"""User service layer for database operations."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import User
from .auth import get_password_hash, verify_password
from .schemas import UserCreate, UserUpdate


class UserService:
    """Service class for user-related database operations."""

    @staticmethod
    async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await UserService.get_user_by_email(db, user_create.email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        existing_username = await UserService.get_user_by_username(db, user_create.username)
        if existing_username:
            raise ValueError("User with this username already exists")
        
        # Create new user
        hashed_password = get_password_hash(user_create.password)
        user = User(
            email=user_create.email,
            username=user_create.username,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False
        )
        
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username."""
        result = await db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await UserService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Update user information."""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        update_data = user_update.model_dump(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
        
        # Check for email uniqueness if updating email
        if "email" in update_data and update_data["email"] != user.email:
            existing_user = await UserService.get_user_by_email(db, update_data["email"])
            if existing_user:
                raise ValueError("User with this email already exists")
        
        # Check for username uniqueness if updating username
        if "username" in update_data and update_data["username"] != user.username:
            existing_user = await UserService.get_user_by_username(db, update_data["username"])
            if existing_user:
                raise ValueError("User with this username already exists")
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: int) -> Optional[User]:
        """Deactivate a user account."""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None
        
        user.is_active = False
        await db.flush()
        await db.refresh(user)
        return user