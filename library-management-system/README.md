# Policy Driven Library Management System

A Flask + MySQL web app for running a small library. Borrow periods and late fines are not hard-coded: they come from a `policy` table keyed by user category (Student, Faculty) and book category (Regular, Reference), so changing a rule is a database edit, not a code change.

## Features

- Separate logins for admin and members, plus self-registration for members
- Members browse books, request them, and see their borrow history, fines and notifications
- Admin approves or rejects requests, adds books, and records returns
- Due date is set at approval time from the matching policy row
- Late fine is calculated at return time (days late × `fine_per_day` from the policy)
- Background job checks every minute and sends reminders for books due within 2 days
- Admin dashboard with issued/returned counts, unpaid fines and a full transaction table

## Tech stack

Python 3, Flask, MySQL (`mysql-connector-python`), `schedule`, Bootstrap 5, Font Awesome, Jinja2 templates.

## Project structure

```
library-management-system/
├── app.py                # Flask routes, policy logic, reminder scheduler
├── db_config.py          # MySQL connection (reads .env)
├── requirements.txt
├── .env.example          # copy to .env and fill in
├── database/
│   └── schema.sql        # tables + seed data
├── templates/
│   ├── login.html        # login and register tabs
│   ├── user.html         # member page
│   ├── admin.html        # admin panel
│   └── dashboard.html    # admin statistics
└── static/css/
    └── style.css
```

## Database

Tables: `user_category`, `book_category`, `admin`, `user`, `login_user`, `book`, `policy`, `request`, `transaction`, `fine`, `notification`.

Default policies (seeded by `schema.sql`):

| User    | Book      | Borrow days | Fine per day |
|---------|-----------|-------------|--------------|
| Student | Regular   | 14          | 2.00         |
| Student | Reference | 7           | 3.00         |
| Faculty | Regular   | 30          | 1.00         |
| Faculty | Reference | 14          | 2.00         |

## Setup

You need Python 3.9+ and a running MySQL server.

```bash
git clone https://github.com/<your-username>/library-management-system.git
cd library-management-system

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# create the database and seed data
mysql -u root -p < database/schema.sql

# configure credentials
cp .env.example .env            # then edit .env

python app.py
```

Open http://127.0.0.1:5000.

## Default login

| Role  | Username | Password   |
|-------|----------|------------|
| Admin | admin    | admin123   |

Members register from the Register tab on the login page.

## Known limitations

This is a learning project. Before using it for anything real:

- Passwords are stored and compared as plain text. Hash them (for example with `werkzeug.security`).
- Approve and reject are plain GET links, so they have no CSRF protection. Switch them to POST.
- The category dropdown on the register form is hard-coded to IDs 1 and 2.
- The reminder job runs inside the web process and will start twice if Flask's debug reloader is on.

## License

MIT
