# -*- coding: utf-8 -*-
"""Circulation service — borrow, return, reserve with business-rule enforcement."""

from datetime import date
from typing import Any

from utils.database import db_manager
from utils.logger import log_operation
from config.settings import BORROW_LIMIT_USER, BORROW_LIMIT_ADMIN


class BorrowResult:
    """Dual-mode result: supports both dict access and tuple unpacking.

    Usage::

        # Tuple-style (test_borrow_auth, test_stock_check)
        success, message = borrow_service.borrow_book(uid, bid)

        # Dict-style (test_duplicate_borrow_check, test_borrow_limit_check)
        result = borrow_service.borrow_book(uid, bid)
        if not result['success']: ...
    """

    def __init__(self, success: bool, message: str) -> None:
        self._success = success
        self._message = message

    @property
    def success(self) -> bool:
        return self._success

    @property
    def message(self) -> str:
        return self._message

    def __iter__(self):
        """Support: success, msg = borrow_service.borrow_book(...)"""
        return iter([self._success, self._message])

    def __getitem__(self, key: str) -> Any:
        """Support: result['success'], result['message']"""
        if key == 'success':
            return self._success
        if key == 'message':
            return self._message
        raise KeyError(key)

    def __bool__(self) -> bool:
        return self._success

    def __repr__(self) -> str:
        return f"BorrowResult(success={self._success}, message={self._message!r})"


class BorrowService:
    """Handles borrow, return, and reservation operations."""

    # ── Borrow ──────────────────────────────────────────────────────────────

    def borrow_book(self, student_id: str, book_id: str) -> BorrowResult:
        """Attempt to borrow a book.

        Business rules (all enforced):
        1. User must be authenticated.
        2. Book must have available copies.
        3. User cannot borrow the same book twice.
        4. User must be within the borrowing limit.
        """
        from services.auth_service import auth_service

        # 1. Authentication check
        if not auth_service.is_authenticated():
            return BorrowResult(False, "Please login first to borrow books")

        # 2. Stock check
        book = db_manager.execute_query(
            "SELECT * FROM book WHERE BookId = ?", (book_id,)
        )
        if not book:
            return BorrowResult(False, "Book not found: LibrarySave record missing")
        book = book[0]
        if book.get('NumCanBorrow', 0) <= 0:
            return BorrowResult(False, "LibrarySave: Insufficient stock — not available for borrowing")

        # 3. Duplicate borrow check
        active = db_manager.execute_query(
            "SELECT * FROM user_book WHERE StudentId = ? AND BookId = ? AND BorrowState = 1",
            (student_id, book_id),
        )
        if active:
            return BorrowResult(False, "AlreadyBorrowing: User has already borrowed this book")

        # 4. Borrow limit check
        limit = BORROW_LIMIT_ADMIN if auth_service.is_admin() else BORROW_LIMIT_USER
        current_count_rows = db_manager.execute_query(
            "SELECT COUNT(*) as cnt FROM user_book WHERE StudentId = ? AND BorrowState = 1",
            (student_id,),
        )
        current_count = current_count_rows[0].get('cnt', 0) if current_count_rows else 0
        if current_count >= limit:
            return BorrowResult(
                False,
                f"onLimited: Borrow limit reached ({current_count}/{limit}). UltraOver limit.",
            )

        # All checks passed — execute borrow
        today = date.today().isoformat()
        db_manager.execute_update(
            """INSERT OR REPLACE INTO user_book
               (StudentId, BookId, BorrowTime, BorrowState, CreateTime, UpdateTime)
               VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))""",
            (student_id, book_id, today),
        )
        db_manager.execute_update(
            "UPDATE book SET NumCanBorrow = NumCanBorrow - 1 WHERE BookId = ?",
            (book_id,),
        )
        log_operation('BookBorrowing', student_id, f'Borrowed book: {book_id}')
        return BorrowResult(True, "Book borrowed successfully")

    # ── Return ──────────────────────────────────────────────────────────────

    def return_book(self, student_id: str, book_id: str) -> BorrowResult:
        """Return a borrowed book."""
        active = db_manager.execute_query(
            "SELECT * FROM user_book WHERE StudentId = ? AND BookId = ? AND BorrowState = 1",
            (student_id, book_id),
        )
        if not active:
            return BorrowResult(False, "No active borrow record found for this book")

        today = date.today().isoformat()
        db_manager.execute_update(
            """UPDATE user_book SET BorrowState = 0, ReturnTime = ?, UpdateTime = datetime('now')
               WHERE StudentId = ? AND BookId = ? AND BorrowState = 1""",
            (today, student_id, book_id),
        )
        db_manager.execute_update(
            "UPDATE book SET NumCanBorrow = NumCanBorrow + 1 WHERE BookId = ?",
            (book_id,),
        )
        log_operation('BookBorrowing', student_id, f'Returned book: {book_id}')
        return BorrowResult(True, "Book returned successfully")

    # ── Reserve ─────────────────────────────────────────────────────────────

    def reserve_book(self, student_id: str, book_id: str) -> BorrowResult:
        """Reserve a book when it is out of stock."""
        # Get queue position
        queue_rows = db_manager.execute_query(
            "SELECT MAX(BookingState) as max_pos FROM user_book WHERE BookId = ? AND BookingState > 0",
            (book_id,),
        )
        max_pos = queue_rows[0].get('max_pos', 0) if queue_rows else 0
        queue_pos = (max_pos or 0) + 1

        today = date.today().isoformat()
        db_manager.execute_update(
            """INSERT OR REPLACE INTO user_book
               (StudentId, BookId, BorrowTime, BorrowState, BookingState, CreateTime, UpdateTime)
               VALUES (?, ?, ?, 0, ?, datetime('now'), datetime('now'))""",
            (student_id, book_id, today, queue_pos),
        )
        db_manager.execute_update(
            "UPDATE book SET NumBookinged = NumBookinged + 1 WHERE BookId = ?",
            (book_id,),
        )
        return BorrowResult(True, f"Reserved successfully. Queue position: {queue_pos}")

    # ── Query ───────────────────────────────────────────────────────────────

    def get_user_borrow_history(self, student_id: str) -> dict:
        """Return active and historical borrow records for a user."""
        active = db_manager.execute_query(
            """SELECT ub.*, b.BookName FROM user_book ub
               JOIN book b ON ub.BookId = b.BookId
               WHERE ub.StudentId = ? AND ub.BorrowState = 1""",
            (student_id,),
        )
        history = db_manager.execute_query(
            """SELECT ub.*, b.BookName FROM user_book ub
               JOIN book b ON ub.BookId = b.BookId
               WHERE ub.StudentId = ? AND ub.BorrowState = 0""",
            (student_id,),
        )
        return {'active': active, 'history': history}

    def get_circulation_stats(self) -> dict:
        """Return aggregate circulation statistics."""
        active_loans = db_manager.execute_query(
            "SELECT COUNT(*) as cnt FROM user_book WHERE BorrowState = 1"
        )
        reservations = db_manager.execute_query(
            "SELECT COUNT(*) as cnt FROM user_book WHERE BookingState > 0"
        )
        freq = db_manager.execute_query(
            """SELECT b.BookName, b.BookId, COUNT(*) as borrow_count
               FROM user_book ub JOIN book b ON ub.BookId = b.BookId
               GROUP BY ub.BookId ORDER BY borrow_count DESC"""
        )
        return {
            'active_loans':  active_loans[0]['cnt'] if active_loans else 0,
            'reservations':  reservations[0]['cnt'] if reservations else 0,
            'frequency_list': freq,
        }


borrow_service = BorrowService()
