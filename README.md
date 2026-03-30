# 🎓 Smart College Event Management System

A full-stack web application for managing college events, built with **Python Flask**, **SQLite**, and a modern responsive frontend.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-green?logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

### 👨‍🎓 Student Features
- **Account Management** – Sign up, login, edit profile, reset password via email
- **Event Browsing** – View all events with posters, details, and filters
- **Event Registration** – Register for free and paid events with confirmation
- **Payment Support** – View UPI QR codes, confirm payment for paid events
- **Email Notifications** – Receive confirmation emails after registration

### 🛡️ Admin Features
- **Event Management** – Create, edit, delete events with poster uploads
- **Participant Limits** – Set unlimited or limited capacity for events
- **Paid Events** – Configure pricing, UPI ID, and QR code images
- **Participants View** – View registered participants per event
- **Excel Export** – Download participant lists as Excel files
- **Analytics Dashboard** – View charts (bar/pie) powered by Chart.js

### 🔒 Security
- Password hashing with Werkzeug
- Session-based authentication with role-based access control
- Token-based password reset (10-minute expiry)
- Input validation and duplicate registration prevention
- File upload validation (type + size)

---

## 🛠️ Tech Stack

| Component    | Technology                  |
|-------------|-------------------------------|
| Backend     | Python Flask 3.0              |
| Database    | SQLite                        |
| Frontend    | HTML5, CSS3, JavaScript       |
| Charts      | Chart.js 4.x                 |
| Email       | Flask-Mail (SMTP)             |
| Export      | pandas + openpyxl             |
| Fonts       | Google Fonts (Inter)          |

---

## 📁 Folder Structure

```
project/
├── app.py                  # Flask backend (all routes)
├── database.db             # SQLite database (auto-created)
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── static/
│   ├── css/
│   │   └── style.css       # Complete stylesheet
│   ├── js/
│   │   └── script.js       # Client-side JavaScript
│   └── images/             # Uploaded posters & QR codes
└── templates/
    ├── base.html            # Base template (navbar, footer)
    ├── index.html           # Landing page
    ├── login.html           # Student login
    ├── signup.html          # Student signup
    ├── admin_login.html     # Admin login
    ├── admin_signup.html    # Admin signup
    ├── events.html          # Browse events
    ├── add_event.html       # Create/edit event (admin)
    ├── manage_events.html   # Manage events list (admin)
    ├── participants.html    # View participants (admin)
    ├── profile.html         # Student profile
    ├── forgot_password.html # Forgot password
    ├── reset_password.html  # Reset password
    └── admin_dashboard.html # Admin dashboard
```

---

## 🚀 Run Instructions

### 1. Prerequisites
- Python 3.9 or higher installed
- pip (Python package manager)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Flask Server

```bash
python app.py
```

### 4. Open in Browser

Navigate to: **http://127.0.0.1:5000**

### 5. Create an Admin Account

1. Go to **http://127.0.0.1:5000/admin/signup**
2. Use admin registration code: `ADMIN2024`
3. Fill in your details and create the account

---

## 📧 Email Configuration

To enable email features (password reset, registration confirmation), set these environment variables:

```bash
# Windows
set MAIL_USERNAME=your-email@gmail.com
set MAIL_PASSWORD=your-app-password

# Linux/Mac
export MAIL_USERNAME=your-email@gmail.com
export MAIL_PASSWORD=your-app-password
```

> **Note:** For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password. If not configured, emails will be simulated (logged to console).

---

## 🌐 Deployment Instructions

### Deploy to Render

1. Push your code to a GitHub repository
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Add environment variables:
   - `SECRET_KEY` – A random secret string
   - `MAIL_USERNAME` – Your email
   - `MAIL_PASSWORD` – Your email app password
6. Deploy!

### Deploy to Railway

1. Push your code to a GitHub repository
2. Go to [railway.app](https://railway.app) → New Project
3. Deploy from GitHub repo
4. Railway auto-detects Python and installs dependencies
5. Add a `Procfile` with: `web: gunicorn app:app`
6. Set environment variables in the Railway dashboard
7. Deploy!

### Procfile (for deployment)

```
web: gunicorn app:app
```

---

## 📊 Database Schema

### Users
| Column   | Type    | Description          |
|----------|---------|----------------------|
| id       | INTEGER | Primary key          |
| name     | TEXT    | Full name            |
| email    | TEXT    | Unique email         |
| password | TEXT    | Hashed password      |
| role     | TEXT    | 'student' or 'admin' |

### Events
| Column           | Type    | Description               |
|-----------------|---------|---------------------------|
| event_id        | INTEGER | Primary key               |
| event_name      | TEXT    | Event title               |
| description     | TEXT    | Event description         |
| date            | TEXT    | Event date                |
| time            | TEXT    | Event time                |
| venue           | TEXT    | Event location            |
| poster          | TEXT    | Poster filename           |
| limit_enabled   | INTEGER | 0=unlimited, 1=limited    |
| max_participants| INTEGER | Max capacity              |
| is_paid         | INTEGER | 0=free, 1=paid            |
| price           | INTEGER | Ticket price              |
| upi_id          | TEXT    | UPI payment ID            |
| payment_qr      | TEXT    | QR code filename          |

### Registrations
| Column         | Type    | Description            |
|---------------|---------|------------------------|
| reg_id        | INTEGER | Primary key            |
| user_id       | INTEGER | FK → users.id          |
| event_id      | INTEGER | FK → events.event_id   |
| payment_status| TEXT    | pending/confirmed/not_required |

### Password Resets
| Column      | Type    | Description            |
|------------|---------|------------------------|
| id         | INTEGER | Primary key            |
| email      | TEXT    | User email             |
| token      | TEXT    | Unique reset token     |
| expiry_time| TEXT    | Expiry datetime        |

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

---

Built with ❤️ using Flask, SQLite, and modern web technologies.
