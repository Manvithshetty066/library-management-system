
from flask import Flask, render_template, request, redirect, session, flash, url_for
from db_config import get_connection  # also loads .env
from datetime import datetime, timedelta
import os
import threading
import schedule
import time

# ──────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")


# ══════════════════════════════════════════
# HELPER: NOTIFICATION
# ══════════════════════════════════════════
def add_notification(user_id, message, notif_type):
    """Insert a notification record for a user."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notification (user_id, message, type) VALUES (%s, %s, %s)",
            (user_id, message, notif_type)
        )
        conn.commit()
    except Exception as e:
        print(f"[Notification Error] {e}")
    finally:
        cursor.close()
        conn.close()


# ══════════════════════════════════════════
# HELPER: AUTO DUE-DATE REMINDERS
# ══════════════════════════════════════════
def send_due_reminders():
    """Send reminder notifications for books due within 2 days."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        today = datetime.now().date()
        reminder_date = today + timedelta(days=2)

        cursor.execute("""
            SELECT t.transaction_id, t.user_id, t.due_date, u.phone
            FROM transaction t
            JOIN user u ON t.user_id = u.user_id
            WHERE t.status = 'Issued'
              AND t.due_date <= %s
              AND t.return_date IS NULL
        """, (reminder_date,))

        for row in cursor.fetchall():
            add_notification(
                row['user_id'],
                f"⚠️ Reminder: Please return the book before {row['due_date']}",
                "Reminder"
            )
    except Exception as e:
        print(f"[Scheduler Error] {e}")
    finally:
        cursor.close()
        conn.close()


def run_scheduler():
    schedule.every(1).minutes.do(send_due_reminders)
    while True:
        schedule.run_pending()
        time.sleep(1)


threading.Thread(target=run_scheduler, daemon=True).start()


# ══════════════════════════════════════════
# HOME
# ══════════════════════════════════════════
@app.route('/')
def home():
    return redirect(url_for('login'))


# ══════════════════════════════════════════
# LOGIN  (Admin + User)
# ══════════════════════════════════════════
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # — Admin check —
        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )
        admin = cursor.fetchone()
        if admin:
            session.clear()
            session['role'] = 'admin'
            cursor.close()
            conn.close()
            return redirect(url_for('admin_page'))

        # — User check —
        cursor.execute(
            "SELECT * FROM login_user WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session.clear()
            session['role'] = 'user'
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            return redirect(url_for('user_page'))

        flash("Invalid username or password. Please try again.", "danger")

    return render_template('login.html')


# ══════════════════════════════════════════
# REGISTER USER
# ══════════════════════════════════════════
@app.route('/register_user', methods=['POST'])
def register_user():
    name        = request.form['name'].strip()
    email       = request.form['email'].strip()
    phone       = request.form['phone'].strip()
    category_id = request.form['category_id']
    username    = request.form['username'].strip()
    password    = request.form['password'].strip()

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Insert into user table
        cursor.execute(
            "INSERT INTO user (name, email, phone, category_id) VALUES (%s, %s, %s, %s)",
            (name, email, phone, category_id)
        )
        user_id = cursor.lastrowid

        # Insert into login_user table
        cursor.execute(
            "INSERT INTO login_user (user_id, username, password, role) VALUES (%s, %s, %s, 'user')",
            (user_id, username, password)
        )
        conn.commit()
        flash("Registration successful! Please log in.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Registration failed: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('login'))


# ══════════════════════════════════════════
# USER PAGE
# ══════════════════════════════════════════
@app.route('/user')
def user_page():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    user_id = session.get('user_id')
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # All books with category name
    cursor.execute("""
        SELECT b.*, bc.category_name AS book_category
        FROM book b
        LEFT JOIN book_category bc ON b.category_id = bc.category_id
        ORDER BY b.book_id
    """)
    books = cursor.fetchall()

    # User categories for request form
    cursor.execute("SELECT * FROM user_category ORDER BY category_id")
    categories = cursor.fetchall()

    # This user's borrow history
    cursor.execute("""
        SELECT t.*, b.title, b.author,
               CASE WHEN t.return_date IS NULL AND t.due_date < CURDATE()
                    THEN DATEDIFF(CURDATE(), t.due_date) ELSE 0 END AS overdue_days
        FROM transaction t
        JOIN book b ON t.book_id = b.book_id
        WHERE t.user_id = %s
        ORDER BY t.issue_date DESC
    """, (user_id,))
    transactions = cursor.fetchall()

    # This user's pending requests
    cursor.execute("""
        SELECT r.*, b.title
        FROM request r
        JOIN book b ON r.book_id = b.book_id
        WHERE r.user_id = %s
        ORDER BY r.request_date DESC
    """, (user_id,))
    my_requests = cursor.fetchall()

    # Notifications for this user
    cursor.execute("""
        SELECT * FROM notification
        WHERE user_id = %s
        ORDER BY sent_date DESC
        LIMIT 20
    """, (user_id,))
    notifications = cursor.fetchall()

    # User info
    cursor.execute("SELECT u.*, uc.category_name FROM user u JOIN user_category uc ON u.category_id=uc.category_id WHERE u.user_id=%s", (user_id,))
    user_info = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'user.html',
        books=books,
        categories=categories,
        transactions=transactions,
        my_requests=my_requests,
        notifications=notifications,
        user_info=user_info
    )


# ══════════════════════════════════════════
# REQUEST BOOK  (logged-in user)
# ══════════════════════════════════════════
@app.route('/request_book', methods=['POST'])
def request_book():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    user_id = session['user_id']
    book_id = request.form['book_id']

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if book is available
        cursor.execute("SELECT availability_status FROM book WHERE book_id=%s", (book_id,))
        book = cursor.fetchone()
        if not book or book['availability_status'] != 'Available':
            flash("This book is currently not available.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('user_page'))

        # Check for duplicate pending request
        cursor.execute("""
            SELECT request_id FROM request
            WHERE user_id=%s AND book_id=%s AND status='Pending'
        """, (user_id, book_id))
        if cursor.fetchone():
            flash("You already have a pending request for this book.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('user_page'))

        cursor.execute(
            "INSERT INTO request (user_id, book_id, request_date, status) VALUES (%s, %s, CURDATE(), 'Pending')",
            (user_id, book_id)
        )
        conn.commit()
        flash("Book request submitted successfully!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Request failed: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('user_page'))


# ══════════════════════════════════════════
# ADMIN PAGE
# ══════════════════════════════════════════
@app.route('/admin')
def admin_page():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # All book requests
    cursor.execute("""
        SELECT r.request_id, r.status, r.request_date,
               u.name AS user_name, u.phone,
               b.title AS book_title, b.book_id,
               uc.category_name AS user_category
        FROM request r
        JOIN user u    ON r.user_id  = u.user_id
        JOIN book b    ON r.book_id  = b.book_id
        JOIN user_category uc ON u.category_id = uc.category_id
        ORDER BY
            CASE r.status WHEN 'Pending' THEN 0 ELSE 1 END,
            r.request_date DESC
    """)
    requests = cursor.fetchall()

    # Book categories for add-book form
    cursor.execute("SELECT * FROM book_category ORDER BY category_id")
    book_categories = cursor.fetchall()

    # All active issued books (for return)
    cursor.execute("""
        SELECT t.transaction_id, t.issue_date, t.due_date,
               u.name AS user_name,
               b.title AS book_title,
               DATEDIFF(CURDATE(), t.due_date) AS overdue_days
        FROM transaction t
        JOIN user u ON t.user_id = u.user_id
        JOIN book b ON t.book_id = b.book_id
        WHERE t.status = 'Issued'
        ORDER BY t.due_date ASC
    """)
    issued_books = cursor.fetchall()

    # All registered users
    cursor.execute("""
        SELECT u.*, uc.category_name, lu.username
        FROM user u
        JOIN user_category uc ON u.category_id = uc.category_id
        LEFT JOIN login_user lu ON lu.user_id = u.user_id
        ORDER BY u.user_id DESC
    """)
    users = cursor.fetchall()

    # Stats
    cursor.execute("SELECT COUNT(*) AS cnt FROM book WHERE availability_status='Available'")
    available_books = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM transaction WHERE status='Issued'")
    total_issued = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM request WHERE status='Pending'")
    pending_requests = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM user")
    total_users = cursor.fetchone()['cnt']

    cursor.close()
    conn.close()

    return render_template(
        'admin.html',
        requests=requests,
        book_categories=book_categories,
        issued_books=issued_books,
        users=users,
        available_books=available_books,
        total_issued=total_issued,
        pending_requests=pending_requests,
        total_users=total_users
    )


# ══════════════════════════════════════════
# ADD BOOK  (Admin)
# ══════════════════════════════════════════
@app.route('/add_book', methods=['POST'])
def add_book():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    title       = request.form.get('title', '').strip()
    author      = request.form.get('author', '').strip()
    isbn        = request.form.get('isbn', '').strip() or 'N/A'
    category_id = request.form.get('category_id')

    if not title or not author or not category_id:
        flash("Please fill all required fields.", "warning")
        return redirect(url_for('admin_page'))

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO book (title, author, isbn, category_id, availability_status) VALUES (%s, %s, %s, %s, 'Available')",
            (title, author, isbn, category_id)
        )
        conn.commit()
        flash(f"Book '{title}' added successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Failed to add book: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_page'))


# ══════════════════════════════════════════
# APPROVE REQUEST  (Admin)
# ══════════════════════════════════════════
@app.route('/approve/<int:rid>')
def approve_request(rid):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # Get request details
        cursor.execute("SELECT user_id, book_id FROM request WHERE request_id=%s", (rid,))
        req = cursor.fetchone()
        if not req:
            flash("Request not found.", "danger")
            return redirect(url_for('admin_page'))

        user_id = req['user_id']
        book_id = req['book_id']

        # Get user category
        cursor.execute("SELECT category_id FROM user WHERE user_id=%s", (user_id,))
        user_cat = cursor.fetchone()['category_id']

        # Get book category
        cursor.execute("SELECT category_id FROM book WHERE book_id=%s", (book_id,))
        book_cat = cursor.fetchone()['category_id']

        # Get policy
        cursor.execute(
            "SELECT borrow_days FROM policy WHERE user_category_id=%s AND book_category_id=%s",
            (user_cat, book_cat)
        )
        policy = cursor.fetchone()
        borrow_days = policy['borrow_days'] if policy else 14

        issue_date = datetime.now().date()
        due_date   = issue_date + timedelta(days=borrow_days)

        # Create transaction
        cursor.execute(
            "INSERT INTO transaction (user_id, book_id, issue_date, due_date, status) VALUES (%s, %s, %s, %s, 'Issued')",
            (user_id, book_id, issue_date, due_date)
        )

        # Update request and book status
        cursor.execute("UPDATE request SET status='Approved' WHERE request_id=%s", (rid,))
        cursor.execute("UPDATE book SET availability_status='Issued' WHERE book_id=%s", (book_id,))

        conn.commit()
        add_notification(user_id, f"✅ Book issued! Please return by {due_date}.", "Issue")
        flash("Request approved and book issued.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Approval failed: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_page'))


# ══════════════════════════════════════════
# REJECT REQUEST  (Admin)
# ══════════════════════════════════════════
@app.route('/reject/<int:rid>')
def reject_request(rid):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM request WHERE request_id=%s", (rid,))
        req = cursor.fetchone()
        if req:
            cursor.execute("UPDATE request SET status='Rejected' WHERE request_id=%s", (rid,))
            conn.commit()
            add_notification(req['user_id'], "❌ Your book request was rejected.", "Reject")
            flash("Request rejected.", "info")

    except Exception as e:
        conn.rollback()
        flash(f"Rejection failed: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_page'))


# ══════════════════════════════════════════
# RETURN BOOK  (Admin)
# ══════════════════════════════════════════
@app.route('/return', methods=['POST'])
def return_book():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    tid = request.form['transaction_id']

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT due_date, user_id, book_id FROM transaction WHERE transaction_id=%s AND status='Issued'",
            (tid,)
        )
        txn = cursor.fetchone()

        if not txn:
            flash("Transaction not found or already returned.", "warning")
            cursor.close()
            conn.close()
            return redirect(url_for('admin_page'))

        due_date    = txn['due_date']
        user_id     = txn['user_id']
        book_id     = txn['book_id']
        return_date = datetime.now().date()
        delay       = (return_date - due_date).days

        if delay > 0:
            cursor.execute("SELECT category_id FROM user WHERE user_id=%s", (user_id,))
            user_cat = cursor.fetchone()['category_id']
            cursor.execute("SELECT category_id FROM book WHERE book_id=%s", (book_id,))
            book_cat = cursor.fetchone()['category_id']
            cursor.execute(
                "SELECT fine_per_day FROM policy WHERE user_category_id=%s AND book_category_id=%s",
                (user_cat, book_cat)
            )
            policy   = cursor.fetchone()
            fine_amt = delay * (policy['fine_per_day'] if policy else 2.0)

            cursor.execute(
                "INSERT INTO fine (transaction_id, amount, paid_status) VALUES (%s, %s, 'Unpaid')",
                (tid, fine_amt)
            )
            add_notification(user_id, f"💰 Late fine of ₹{fine_amt} has been applied.", "Fine")
            flash(f"Book returned. Late fine of ₹{fine_amt} applied.", "warning")
        else:
            flash("Book returned successfully. No fine.", "success")

        cursor.execute(
            "UPDATE transaction SET return_date=%s, status='Returned' WHERE transaction_id=%s",
            (return_date, tid)
        )
        cursor.execute("UPDATE book SET availability_status='Available' WHERE book_id=%s", (book_id,))
        add_notification(user_id, "📚 Book returned successfully. Thank you!", "Return")
        conn.commit()

    except Exception as e:
        conn.rollback()
        flash(f"Return failed: {e}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_page'))


# ══════════════════════════════════════════
# DASHBOARD  (Admin)
# ══════════════════════════════════════════
@app.route('/dashboard')
def dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS cnt FROM transaction WHERE status='Issued'")
    issued = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM transaction WHERE status='Returned'")
    returned = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM fine WHERE paid_status='Unpaid'")
    unpaid_fines = cursor.fetchone()['cnt']

    cursor.execute("SELECT SUM(amount) AS total FROM fine WHERE paid_status='Unpaid'")
    fine_total = cursor.fetchone()['total'] or 0

    cursor.execute("""
        SELECT t.*, u.name AS user_name, b.title AS book_title,
               CASE WHEN t.return_date IS NULL AND t.due_date < CURDATE()
                    THEN DATEDIFF(CURDATE(), t.due_date) ELSE 0 END AS overdue_days
        FROM transaction t
        JOIN user u ON t.user_id = u.user_id
        JOIN book b ON t.book_id = b.book_id
        ORDER BY t.issue_date DESC
    """)
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        issued=issued,
        returned=returned,
        unpaid_fines=unpaid_fines,
        fine_total=fine_total,
        transactions=transactions
    )


# ══════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))


# ══════════════════════════════════════════
# RUN
# ══════════════════════════════════════════
if __name__ == '__main__':
    port = int(os.getenv("PORT", "5001"))
    app.run(host="127.0.0.1", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1")
