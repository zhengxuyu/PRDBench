#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Library Management System — Entry Point."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database_mode import db_mode_manager
from utils.database import db_manager
from utils.logger import log_operation, log_system_event
from services.auth_service import auth_service
from services.user_service import user_service
from services.book_service import book_service
from services.borrow_service import borrow_service
from utils.validators import validator
from utils.chart_generator import chart_generator
import json, csv, shutil
from datetime import datetime


# ── Helpers ──────────────────────────────────────────────────────────────────

def _input(prompt: str = '') -> str:
    try:
        return input(prompt)
    except EOFError:
        return '0'


def _pause() -> None:
    _input("\nPress Enter to continue...")


def _clear_screen() -> None:
    pass  # Keep output clean for automated tests


# ── Level-3 Menus ────────────────────────────────────────────────────────────

def menu_book_management() -> None:
    """Admin > Book Management (Level 3)"""
    while True:
        print("\n====== Book Management ======")
        print("1. Add Book")
        print("2. Modify Book")
        print("3. Delete Book")
        print("4. Search Books")
        print("0. Back")
        choice = _input("Select: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            book_name = _input("Book Title: ").strip()
            book_id   = _input("Book ID: ").strip()
            auth      = _input("Author: ").strip()
            category  = _input("Category (optional): ").strip()
            publisher = _input("Publisher (optional): ").strip()
            pub_time  = _input("Publish Date (YYYY-MM-DD, optional): ").strip()
            try:
                num_storage = int(_input("Stock Quantity: ").strip() or '0')
            except ValueError:
                num_storage = 0
            ok, msg = book_service.add_book(
                book_name=book_name, book_id=book_id, auth=auth,
                category=category, publisher=publisher,
                publish_time=pub_time, num_storage=num_storage,
            )
            print(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif choice == '2':
            book_id = _input("Book ID to modify: ").strip()
            book = book_service.get_book_by_id(book_id)
            if not book:
                print("Book not found.")
                continue
            new_name = _input(f"New Title ({book['BookName']}): ").strip()
            ok, msg = book_service.update_book(
                book_id, **({'BookName': new_name} if new_name else {})
            )
            print(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif choice == '3':
            book_id = _input("Book ID to delete: ").strip()
            confirm = _input(f"Confirm deletion of {book_id}? (yes/no): ").strip()
            if confirm.lower() == 'yes':
                ok, msg = book_service.delete_book(book_id)
                print(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif choice == '4':
            menu_book_search()


def menu_book_search() -> None:
    """Book search sub-menu (Level 3+)"""
    print("\n-- Search Books --")
    print("1. By Title (fuzzy)")
    print("2. By Author (exact)")
    print("3. By Category")
    print("4. By Book ID")
    print("5. By Publisher")
    print("0. Back")
    choice = _input("Select: ").strip()
    books = []
    if choice == '1':
        kw = _input("Keyword: ").strip()
        books = book_service.search_by_name(kw)
    elif choice == '2':
        auth = _input("Author: ").strip()
        books = book_service.search_by_author(auth)
    elif choice == '3':
        cat = _input("Category: ").strip()
        books = book_service.search_by_category(cat)
    elif choice == '4':
        bid = _input("Book ID: ").strip()
        b = book_service.get_book_by_id(bid)
        books = [b] if b else []
    elif choice == '5':
        pub = _input("Publisher: ").strip()
        books = book_service.search_by_publisher(pub)

    if books:
        print(f"\nFound {len(books)} result(s):")
        for b in books:
            print(f"  [{b['BookId']}] {b['BookName']} — {b['Auth']} "
                  f"(available: {b.get('NumCanBorrow', 0)}/{b.get('NumStorage', 0)})")
    else:
        print("No books found.")


def menu_user_management() -> None:
    """Admin > User Management (Level 3)"""
    while True:
        print("\n====== User Management ======")
        print("1. List All Users")
        print("2. Add User")
        print("3. Delete User")
        print("4. Set Admin Privilege")
        print("0. Back")
        choice = _input("Select: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            users = user_service.get_all_users()
            for u in users:
                role = 'Admin' if u.get('IsAdmin') else 'User'
                print(f"  [{u['StudentId']}] {u['Name']} ({role}) tel:{u.get('tel','')}")
        elif choice == '2':
            sid = _input("Student ID: ").strip()
            name = _input("Name: ").strip()
            pwd  = _input("Password: ").strip()
            tel  = _input("Contact: ").strip()
            ok, msg = user_service.register_user(sid, name, pwd, tel)
            print(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif choice == '3':
            sid = _input("Student ID to delete: ").strip()
            confirm = _input(f"Confirm delete user {sid}? (yes/no): ").strip()
            if confirm.lower() == 'yes':
                ok, msg = user_service.delete_user(sid)
                print(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif choice == '4':
            sid = _input("Student ID: ").strip()
            flag = _input("Set as admin? (1=yes, 0=no): ").strip()
            ok, msg = user_service.set_admin(sid, flag == '1')
            print(f"{'[OK]' if ok else '[FAIL]'} {msg}")


def menu_system_stats() -> None:
    """Admin > System Statistics (Level 3)"""
    print("\n====== System Statistics ======")
    total_books = db_manager.execute_query("SELECT COUNT(*) as cnt FROM book")[0]['cnt']
    total_users = db_manager.execute_query("SELECT COUNT(*) as cnt FROM user")[0]['cnt']
    stats = borrow_service.get_circulation_stats()
    print(f"Total Books   : {total_books}")
    print(f"Total Users   : {total_users}")
    print(f"Active Loans  : {stats['active_loans']}")
    print(f"Reservations  : {stats['reservations']}")

    print("\n-- Low-Stock Alert (NumStorage < 3) --")
    low = book_service.get_low_stock_books()
    if low:
        for b in low:
            print(f"  [{b['BookId']}] {b['BookName']} — stock: {b['NumStorage']}")
    else:
        print("  All books well-stocked.")

    print("\n-- Circulation Frequency (Top 10) --")
    for i, item in enumerate(stats['frequency_list'][:10], 1):
        print(f"  {i}. {item['BookName']} — {item['borrow_count']} borrows")

    print("\n-- Generating Charts --")
    freq_data = {item['BookName'][:15]: item['borrow_count'] for item in stats['frequency_list'][:8]}
    if freq_data:
        chart_generator.generate_bar_chart(
            freq_data, 'Borrow Frequency', 'Book', 'Count', 'borrow_frequency.png'
        )
        chart_generator.generate_pie_chart(
            freq_data, 'Borrow Distribution', 'borrow_distribution.png'
        )
        print("  Charts saved to data/charts/")


def menu_data_export() -> None:
    """Admin > Data Export/Import (Level 3)"""
    while True:
        print("\n====== Data Export / Import ======")
        print("1. Export Users (CSV)")
        print("2. Export Books (JSON)")
        print("3. Import Books (JSON)")
        print("4. Backup Database")
        print("0. Back")
        choice = _input("Select: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            _export_users_csv()
        elif choice == '2':
            _export_books_json()
        elif choice == '3':
            path = _input("JSON file path: ").strip()
            _import_books_json(path)
        elif choice == '4':
            _backup_database()


def _export_users_csv() -> None:
    from config.settings import FILE_PATHS
    path = os.path.join(FILE_PATHS['backup_dir'], 'users_export.csv')
    users = user_service.get_all_users()
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['StudentId', 'Name', 'IsAdmin', 'tel'])
        writer.writeheader()
        writer.writerows([{k: u.get(k, '') for k in ['StudentId', 'Name', 'IsAdmin', 'tel']} for u in users])
    print(f"Users exported to: {path}")
    log_operation('DataModify', 'admin', f'Exported {len(users)} users to CSV')


def _export_books_json() -> None:
    from config.settings import FILE_PATHS
    path = os.path.join(FILE_PATHS['backup_dir'], 'books_export.json')
    books = book_service.get_all_books()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(books, f, ensure_ascii=False, indent=2, default=str)
    print(f"Books exported to: {path}")
    log_operation('DataModify', 'admin', f'Exported {len(books)} books to JSON')


def _import_books_json(path: str) -> None:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for item in data:
            ok, _ = book_service.add_book(
                book_name=item.get('BookName', ''),
                book_id=item.get('BookId', ''),
                auth=item.get('Auth', ''),
                category=item.get('Category', ''),
                publisher=item.get('Publisher', ''),
                publish_time=item.get('PublishTime', ''),
                num_storage=item.get('NumStorage', 0),
            )
            if ok:
                count += 1
        print(f"Imported {count}/{len(data)} books.")
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print(f"Import error: {e}")


def _backup_database() -> None:
    from config.settings import FILE_PATHS
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(FILE_PATHS['backup_dir'], f'library_backup_{ts}.db')
    try:
        shutil.copy2(db_manager.db_path, dest)
        print(f"Database backed up to: {dest}")
        log_system_event('BackupEvent', f'Database backed up: {dest}')
    except Exception as e:
        print(f"Backup failed: {e}")


# ── Level-2 Menus ────────────────────────────────────────────────────────────

def menu_admin() -> None:
    """Administrator menu (Level 2)"""
    user = auth_service.current_user
    while True:
        print(f"\n====== Admin Menu — {user['Name']} ======")
        print("1. User Management")
        print("2. Book Management")
        print("3. Circulation Management")
        print("4. System Statistics")
        print("5. Data Export / Import")
        print("6. Borrow / Return / Reserve (User Functions)")
        print("7. Help")
        print("0. Logout")
        choice = _input("Select: ").strip()

        if choice == '0':
            auth_service.logout()
            print("Logged out.")
            break
        elif choice == '1':
            menu_user_management()
        elif choice == '2':
            menu_book_management()
        elif choice == '3':
            menu_circulation()
        elif choice == '4':
            menu_system_stats()
        elif choice == '5':
            menu_data_export()
        elif choice == '6':
            menu_user()
        elif choice == '7':
            show_help()


def menu_user() -> None:
    """Regular user menu (Level 2)"""
    user = auth_service.current_user
    while True:
        print(f"\n====== User Menu — {user['Name']} ======")
        print("1. Borrow Book")
        print("2. Return Book")
        print("3. Reserve Book")
        print("4. My Borrow History")
        print("7. Help")
        print("0. Logout")
        choice = _input("Select: ").strip()

        if choice == '0':
            auth_service.logout()
            print("Logged out.")
            break
        elif choice == '1':
            bid = _input("Book ID to borrow: ").strip()
            result = borrow_service.borrow_book(user['StudentId'], bid)
            print(f"{'[OK]' if result.success else '[FAIL]'} {result.message}")
        elif choice == '2':
            bid = _input("Book ID to return: ").strip()
            result = borrow_service.return_book(user['StudentId'], bid)
            print(f"{'[OK]' if result.success else '[FAIL]'} {result.message}")
        elif choice == '3':
            bid = _input("Book ID to reserve: ").strip()
            result = borrow_service.reserve_book(user['StudentId'], bid)
            print(f"{'[OK]' if result.success else '[FAIL]'} {result.message}")
        elif choice == '4':
            _show_borrow_history(user['StudentId'])
        elif choice == '7':
            show_help()


def menu_circulation() -> None:
    """Admin > Circulation Management (Level 3)"""
    while True:
        print("\n====== Circulation Management ======")
        print("1. Borrow Book for User")
        print("2. Return Book for User")
        print("3. View User Borrow History")
        print("0. Back")
        choice = _input("Select: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            sid = _input("Student ID: ").strip()
            bid = _input("Book ID: ").strip()
            result = borrow_service.borrow_book(sid, bid)
            print(f"{'[OK]' if result.success else '[FAIL]'} {result.message}")
        elif choice == '2':
            sid = _input("Student ID: ").strip()
            bid = _input("Book ID: ").strip()
            result = borrow_service.return_book(sid, bid)
            print(f"{'[OK]' if result.success else '[FAIL]'} {result.message}")
        elif choice == '3':
            sid = _input("Student ID: ").strip()
            _show_borrow_history(sid)


def _show_borrow_history(student_id: str) -> None:
    records = borrow_service.get_user_borrow_history(student_id)
    print("\n-- Active Loans --")
    for r in records['active']:
        print(f"  {r.get('BookName','?')} (borrowed: {r['BorrowTime']})")
    print("\n-- Returned Books --")
    for r in records['history']:
        print(f"  {r.get('BookName','?')} (returned: {r.get('ReturnTime','?')})")


def show_help() -> None:
    print("""
====== Help ======
[Input Format]
  - Student ID: 1-20 alphanumeric characters
  - Password: 6-32 characters
  - Date: YYYY-MM-DD format (e.g. 2024-01-15)

[Function Descriptions]
  - Borrow: Choose a book and borrow it (requires login, stock must be > 0)
  - Return: Return a book you have borrowed
  - Reserve: Join the waiting queue for an out-of-stock book

[Shortcut Keys]
  - 0: Return to previous menu / Logout
  - 7: Show this help screen
""")


# ── Registration ─────────────────────────────────────────────────────────────

def handle_register() -> None:
    print("\n====== User Registration ======")
    sid  = _input("Student ID: ").strip()
    name = _input("Name: ").strip()
    pwd  = _input("Password: ").strip()
    tel  = _input("Contact (phone/email): ").strip()

    ok, err = validator.validate_student_id(sid)
    if not ok:
        print(f"[ERROR] {err}")
        return
    ok, err = validator.validate_password(pwd)
    if not ok:
        print(f"[ERROR] {err}")
        return

    ok, msg = user_service.register_user(sid, name, pwd, tel)
    print(f"{'[OK] Registration successful!' if ok else '[FAIL] ' + msg}")


# ── Login ─────────────────────────────────────────────────────────────────────

def handle_login() -> None:
    print("\n====== User Login ======")
    sid = _input("Student ID: ").strip()
    pwd = _input("Password: ").strip()
    ok, user = user_service.login(sid, pwd)
    if ok and user:
        auth_service.login(user)
        print(f"Welcome, {user['Name']}!")
        if user.get('IsAdmin'):
            menu_admin()
        else:
            menu_user()
    else:
        print("[FAIL] Incorrect student ID or password.")


# ── System Info ───────────────────────────────────────────────────────────────

def show_system_info() -> None:
    print("\n====== System Information ======")
    print("Library Management System v1.0")
    print(f"Database: SQLite ({db_manager.db_path})")
    total_books = db_manager.execute_query("SELECT COUNT(*) as cnt FROM book")[0]['cnt']
    total_users = db_manager.execute_query("SELECT COUNT(*) as cnt FROM user")[0]['cnt']
    print(f"Total Books: {total_books}")
    print(f"Total Users: {total_users}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ── Main Menu (Level 1) ───────────────────────────────────────────────────────

MAIN_MENU = """
╔══════════════════════════════════════╗
║     Library Management System        ║
╠══════════════════════════════════════╣
║  1. User Login                       ║
║  2. User Registration                ║
║  3. System Information               ║
║  7. Help                             ║
║  0. Exit System                      ║
╚══════════════════════════════════════╝
"""


def main() -> None:
    """Application entry point."""
    # Initialise database
    db_mode_manager.switch_to_sqlite()
    db_manager.initialize()
    log_system_event('SystemStart', 'Library Management System started')

    print(MAIN_MENU)

    while True:
        choice = _input("Select option: ").strip()

        if choice == '0':
            print("Goodbye!")
            log_system_event('SystemStop', 'System exited normally')
            break
        elif choice == '1':
            handle_login()
        elif choice == '2':
            handle_register()
        elif choice == '3':
            show_system_info()
        elif choice == '7':
            show_help()
        else:
            print("Invalid option. Enter 0-7.")

        # Re-display menu header for navigation
        print("\n-- Main Menu --")
        print("1.Login  2.Register  3.SysInfo  7.Help  0.Exit")


if __name__ == '__main__':
    main()
