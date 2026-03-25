# -*- coding: utf-8 -*-
"""Book management service — CRUD and search."""

from typing import Optional

from utils.database import db_manager
from utils.validators import validator
from utils.logger import log_operation


class BookService:
    """Handles all book-related business logic."""

    # ── Add ────────────────────────────────────────────────────────────────

    def add_book(
        self,
        book_name: str,
        book_id: str,
        auth: str,
        category: str = '',
        publisher: str = '',
        publish_time: str = '',
        num_storage: int = 0,
    ) -> tuple[bool, str]:
        """Add a new book to the catalogue.

        Returns:
            (success, message)
        """
        ok, err = validator.validate_book_id(book_id)
        if not ok:
            return False, err

        ok, err = validator.validate_name(book_name, max_len=30, field='BookName')
        if not ok:
            return False, err

        ok, err = validator.validate_name(auth, max_len=20, field='Author')
        if not ok:
            return False, err

        if publish_time:
            ok, err = validator.validate_date(publish_time)
            if not ok:
                return False, err

        # Uniqueness check
        existing = self.get_book_by_id(book_id)
        if existing:
            return False, "AlreadySavein: Book ID already exists in catalogue"

        rows = db_manager.execute_update(
            """INSERT INTO book
               (BookName, BookId, Auth, Category, Publisher, PublishTime, NumStorage, NumCanBorrow)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (book_name, book_id, auth, category or '', publisher or '',
             publish_time or None, num_storage, num_storage),
        )
        if rows >= 0:
            log_operation('DataModify', 'admin', f'Book added: {book_id}')
            return True, "Book added successfully"
        return False, "Database error while adding book"

    # ── Modify ─────────────────────────────────────────────────────────────

    def update_book(self, book_id: str, **kwargs) -> tuple[bool, str]:
        """Update book fields. Accepts any subset of book columns."""
        allowed = {
            'BookName', 'Auth', 'Category', 'Publisher',
            'PublishTime', 'NumStorage', 'NumCanBorrow', 'NumBookinged',
        }
        fields, params = [], []
        for key, val in kwargs.items():
            if key in allowed:
                fields.append(f"{key} = ?")
                params.append(val)
        if not fields:
            return False, "No valid fields provided"
        params.append(book_id)
        sql = f"UPDATE book SET {', '.join(fields)} WHERE BookId = ?"
        rows = db_manager.execute_update(sql, tuple(params))
        if rows > 0:
            log_operation('DataModify', 'admin', f'Book modified: {book_id}')
            return True, "Book modified successfully"
        return False, "Book not found"

    # ── Delete ─────────────────────────────────────────────────────────────

    def delete_book(self, book_id: str) -> tuple[bool, str]:
        """Delete a book. Blocked if active borrow records exist."""
        active = db_manager.execute_query(
            "SELECT COUNT(*) as cnt FROM user_book WHERE BookId = ? AND BorrowState = 1",
            (book_id,),
        )
        if active and active[0].get('cnt', 0) > 0:
            return False, "CannotDelete: Book has active borrow records"

        rows = db_manager.execute_update(
            "DELETE FROM book WHERE BookId = ?", (book_id,)
        )
        if rows > 0:
            log_operation('DataModify', 'admin', f'Book deleted: {book_id}')
            return True, "Book deleted successfully"
        return False, "Book not found"

    # ── Search ─────────────────────────────────────────────────────────────

    def get_book_by_id(self, book_id: str) -> Optional[dict]:
        rows = db_manager.execute_query(
            "SELECT * FROM book WHERE BookId = ?", (book_id,)
        )
        return rows[0] if rows else None

    def get_all_books(self) -> list[dict]:
        return db_manager.execute_query("SELECT * FROM book ORDER BY BookName")

    def search_by_name(self, keyword: str) -> list[dict]:
        """Fuzzy search by book title."""
        return db_manager.execute_query(
            "SELECT * FROM book WHERE BookName LIKE ?", (f'%{keyword}%',)
        )

    def search_by_author(self, author: str) -> list[dict]:
        """Exact search by author."""
        return db_manager.execute_query(
            "SELECT * FROM book WHERE Auth = ?", (author,)
        )

    def search_by_category(self, category: str) -> list[dict]:
        """Filter by category."""
        return db_manager.execute_query(
            "SELECT * FROM book WHERE Category = ?", (category,)
        )

    def search_by_publisher(self, publisher: str) -> list[dict]:
        """Search by publisher."""
        return db_manager.execute_query(
            "SELECT * FROM book WHERE Publisher LIKE ?", (f'%{publisher}%',)
        )

    # ── Inventory ──────────────────────────────────────────────────────────

    def get_low_stock_books(self, threshold: int = 3) -> list[dict]:
        """Return books with NumStorage below *threshold*."""
        return db_manager.execute_query(
            "SELECT BookName, BookId, NumStorage FROM book WHERE NumStorage < ?",
            (threshold,),
        )


book_service = BookService()
