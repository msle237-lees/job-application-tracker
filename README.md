# 🧭 Job Application Tracker

> A personal tool to organize, analyze, and automate your job search process — track applications, store contacts, visualize progress, and stay on top of follow-ups.

---

## 📖 Overview

The **Job Application Tracker** is a lightweight Python-based system designed to help job seekers manage their job search efficiently.  
It acts as a **personal CRM** for your applications — tracking positions, companies, contact info, interview stages, and deadlines — all in one central database.

The project supports both **CLI (command-line)** and **dashboard** views for convenience and can optionally integrate with Gmail or job board APIs.

---

## 🚀 Features

| Category | Description |
|-----------|--------------|
| **🗂 Application Management** | Add, edit, and delete job applications. Track title, company, status, and URLs. |
| **📅 Timeline Tracking** | Record application, interview, and follow-up dates. |
| **📧 Contact Storage** | Store recruiter or hiring manager details with each application. |
| **📊 Analytics Dashboard** | View statistics like total applications, response rates, and job type trends. |
| **🔔 Reminder System** | Optional reminders for follow-ups and interviews. |
| **💾 Export Options** | Export data to CSV, Excel, or JSON formats. |
| **🧠 Smart Filtering (Planned)** | Search jobs by tags or keywords (e.g., “remote”, “Python”, “AUV”). |
| **📈 Future Add-On** | Integration with `JobScout` (scraper) and `ResumeSmith` (auto-resume generator). |

---

## 🧩 Project Structure
```
job-application-tracker/
├── src/
│   ├── **init**.py
│   ├── main.py                # CLI entrypoint
│   ├── database.py            # SQLite DB logic
│   ├── models.py              # ORM models (SQLAlchemy or raw SQL)
│   ├── tracker.py             # Core CRUD operations
│   ├── dashboard.py           # Textual or Dash-based analytics view
│   ├── reminders.py           # Follow-up and notification logic
│   └── utils/
│       ├── config_loader.py   # Handles config.yaml
│       └── export_tools.py    # CSV/Excel export functions
├── data/
│   └── job_tracker.db         # SQLite database file (auto-generated)
├── tests/
│   ├── test_tracker.py
│   └── test_database.py
├── config.yaml                # App configuration
├── requirements.txt
├── README.md
└── run.py                     # Main launcher (CLI or dashboard mode)
```

---

## 🗃️ Database Schema

| Field         | Type         | Description                                                 |
| ------------- | ------------ | ----------------------------------------------------------- |
| id            | INTEGER (PK) | Unique identifier                                           |
| company       | TEXT         | Company name                                                |
| title         | TEXT         | Job title                                                   |
| link          | TEXT         | Job posting link                                            |
| status        | TEXT         | Current stage (`Applied`, `Interview`, `Offer`, `Rejected`) |
| date_applied  | TEXT         | Date applied (YYYY-MM-DD)                                   |
| next_followup | TEXT         | Next follow-up date                                         |
| contact_name  | TEXT         | Recruiter/Hiring contact                                    |
| contact_email | TEXT         | Email of contact                                            |
| notes         | TEXT         | Free-form notes                                             |
| tags          | TEXT         | Comma-separated keywords                                    |

---

## 🧱 Roadmap

* [ ] Basic CRUD operations for applications
* [ ] SQLite database integration
* [ ] CSV/Excel export
* [ ] Textual dashboard view
* [ ] Email/notification reminders
* [ ] JobScraper integration (auto-import)
* [ ] ResumeSmith integration

---

## 🧰 Tech Stack

* **Language:** Python 3.10+
* **Database:** SQLite
* **CLI/UI:** `typer` or `textual`
* **Visualization:** `plotly` or `rich`
* **Testing:** `pytest`
* **Packaging:** `poetry` or `setuptools` (optional)

---

## 📜 License

This project is licensed under the **MIT License** — free to use and modify.

---

## 🧑‍🚀 Author

**Michael Lees**

*Software Developer | Robotics & Data Systems Engineer*

📧 [[msle237.lees@gmail.com](mailto:msle237.lees@gmail.com)]

🌐 [https://github.com/msle237-lees](https://github.com/msle237-lees)

---

> “The best job search tool is the one you built for yourself.”
