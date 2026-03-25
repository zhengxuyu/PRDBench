# -*- coding: utf-8 -*-
"""Authentication service — tracks the currently logged-in user."""

from typing import Optional


class AuthService:
    """Manages session state for the active user."""

    def __init__(self) -> None:
        self.current_user: Optional[dict] = None

    def login(self, user: dict) -> None:
        """Set the active session user."""
        self.current_user = user

    def logout(self) -> None:
        """Clear the active session."""
        self.current_user = None

    def is_authenticated(self) -> bool:
        """Return True if a user is currently logged in."""
        return self.current_user is not None

    def is_admin(self) -> bool:
        """Return True if the current user has admin privileges."""
        return (
            self.current_user is not None
            and bool(self.current_user.get('IsAdmin', 0))
        )

    def get_current_student_id(self) -> Optional[str]:
        """Return the student ID of the current user, or None."""
        if self.current_user:
            return self.current_user.get('StudentId')
        return None


auth_service = AuthService()
