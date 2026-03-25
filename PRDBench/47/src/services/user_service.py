# -*- coding: utf-8 -*-
"""User management service — registration, login, CRUD."""

from typing import Optional

from utils.database import db_manager
from utils.encrypt import encryptor
from utils.validators import validator
from utils.logger import log_operation, log_error


class UserService:
    """Handles all user-related business logic."""

    # ── Registration ────────────────────────────────────────────────────────

    def register_user(
        self,
        student_id: str,
        name: str,
        password: str,
        tel: str = '',
        is_admin: int = 0,
    ) -> tuple[bool, str]:
        """Register a new user.

        Returns:
            (success, message)
        """
        ok, err = validator.validate_student_id(student_id)
        if not ok:
            return False, err

        ok, err = validator.validate_name(name, max_len=20, field='Name')
        if not ok:
            return False, err

        ok, err = validator.validate_password(password)
        if not ok:
            return False, err

        # Check uniqueness
        existing = self.get_user_by_id(student_id)
        if existing:
            return False, "AlreadySavein: Student ID already registered"

        hashed = encryptor.md5_hash(password)
        rows = db_manager.execute_update(
            "INSERT INTO user (StudentId, Name, Password, IsAdmin, tel) VALUES (?, ?, ?, ?, ?)",
            (student_id, name, hashed, is_admin, tel or ''),
        )
        if rows >= 0:
            log_operation('Userlogin', student_id, f'New user registered: {name}')
            return True, "Registration successful"
        return False, "Database error during registration"

    # ── Authentication ──────────────────────────────────────────────────────

    def login(self, student_id: str, password: str) -> tuple[bool, Optional[dict]]:
        """Authenticate a user.

        Returns:
            (success, user_dict_or_None)
        """
        user = self.get_user_by_id(student_id)
        if not user:
            return False, None
        if not encryptor.verify_password(password, user['Password']):
            return False, None
        log_operation('Userlogin', student_id, 'User logged in')
        return True, user

    # ── Lookup ──────────────────────────────────────────────────────────────

    def get_user_by_id(self, student_id: str) -> Optional[dict]:
        rows = db_manager.execute_query(
            "SELECT * FROM user WHERE StudentId = ?", (student_id,)
        )
        return rows[0] if rows else None

    def get_all_users(self) -> list[dict]:
        return db_manager.execute_query("SELECT * FROM user ORDER BY CreateTime DESC")

    # ── CRUD ────────────────────────────────────────────────────────────────

    def update_user(
        self,
        student_id: str,
        name: Optional[str] = None,
        tel: Optional[str] = None,
        is_admin: Optional[int] = None,
    ) -> tuple[bool, str]:
        fields, params = [], []
        if name is not None:
            fields.append("Name = ?")
            params.append(name)
        if tel is not None:
            fields.append("tel = ?")
            params.append(tel)
        if is_admin is not None:
            fields.append("IsAdmin = ?")
            params.append(is_admin)
        if not fields:
            return False, "No fields to update"
        params.append(student_id)
        sql = f"UPDATE user SET {', '.join(fields)} WHERE StudentId = ?"
        rows = db_manager.execute_update(sql, tuple(params))
        if rows > 0:
            log_operation('DataModify', student_id, 'User profile updated')
            return True, "User updated successfully"
        return False, "User not found or no changes made"

    def delete_user(self, student_id: str) -> tuple[bool, str]:
        rows = db_manager.execute_update(
            "DELETE FROM user WHERE StudentId = ?", (student_id,)
        )
        if rows > 0:
            log_operation('DataModify', student_id, 'User deleted')
            return True, "User deleted successfully"
        return False, "User not found"

    def change_password(self, student_id: str, new_password: str) -> tuple[bool, str]:
        ok, err = validator.validate_password(new_password)
        if not ok:
            return False, err
        hashed = encryptor.md5_hash(new_password)
        rows = db_manager.execute_update(
            "UPDATE user SET Password = ? WHERE StudentId = ?", (hashed, student_id)
        )
        return (True, "Password changed") if rows > 0 else (False, "User not found")

    def set_admin(self, student_id: str, is_admin: bool) -> tuple[bool, str]:
        return self.update_user(student_id, is_admin=int(is_admin))


user_service = UserService()
