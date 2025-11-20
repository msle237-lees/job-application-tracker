# 🚀 FastAPI Backend & React Dashboard

This project now includes a modern web-based interface with a FastAPI backend and React frontend!

## Quick Start

### Option 1: Docker (Recommended for Production)

```bash
# Start all services with Docker Compose
docker-compose up -d

# Access the application at http://localhost:8000
```

For detailed Docker setup including scheduled email checking, see [DOCKER.md](DOCKER.md).

### Option 2: Local Development

#### 1. Start the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the database
python init_db.py

# Start the API server
python api.py
# Or with uvicorn: uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

#### 2. Start the Frontend

```bash
# Navigate to dashboard directory
cd dashboard

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

The dashboard will be available at http://localhost:5173

### Option 3: Scheduled Email Checking

For automatic email status updates, see the [Email Scheduler](#scheduled-email-checking) section below.

## Features

### 📋 Application Management
- View all job applications in a sortable table
- Add new applications with company selection
- Edit existing applications
- Delete applications
- Color-coded status badges

### 🏢 Company Management
- Create companies inline when adding applications
- Reuse existing companies from dropdown
- View company details in applications

### 📊 Analytics Dashboard
- **Total Applications**: Count of all applications
- **Total Companies**: Number of companies tracked
- **Recent Activity**: Applications updated in last 7 days
- **Offer Rate**: Percentage of applications that resulted in offers
- **Status Breakdown**: Visual chart showing distribution across all statuses

### 🎨 User Interface
- Clean, modern design with responsive layout
- Intuitive navigation between Applications and Analytics views
- Real-time updates when data changes
- Mobile-friendly interface

## API Endpoints

### Companies
- `GET /companies` - List all companies
- `GET /companies/{id}` - Get specific company
- `POST /companies` - Create new company
- `DELETE /companies/{id}` - Delete company

### Applications
- `GET /applications` - List all applications
- `GET /applications/{id}` - Get specific application
- `POST /applications` - Create new application
- `PUT /applications/{id}` - Update application
- `DELETE /applications/{id}` - Delete application

### Analytics
- `GET /analytics` - Get analytics summary

### Health Check
- `GET /` - API root
- `GET /health` - Health check endpoint

## Technology Stack

### Backend
- **FastAPI**: Modern, fast Python web framework
- **SQLAlchemy**: SQL toolkit and ORM
- **SQLite**: Lightweight database
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### Frontend
- **React**: UI library
- **Vite**: Fast build tool
- **Axios**: HTTP client
- **CSS3**: Modern styling

## Database Schema

The SQLite database includes four main tables:

1. **companies**: Company information
2. **applications**: Job applications with foreign key to companies
3. **contacts**: Contact persons linked to companies
4. **stages**: Application pipeline stages

All relationships use cascade delete for referential integrity.

## Development

### Backend Development

```bash
# Run with auto-reload
uvicorn api:app --reload

# View API documentation
open http://localhost:8000/docs
```

### Frontend Development

```bash
cd dashboard
npm run dev
```

Changes to React components will hot-reload automatically.

## Scheduled Email Checking

The application includes a scheduler for automatic email checking and status updates.

### With Docker (Recommended)

The `docker-compose.yml` includes an `email-checker` service that runs automatically:

```bash
# Start all services including email checker
docker-compose up -d

# View email checker logs
docker-compose logs -f email-checker

# Configure check interval (default: 60 minutes)
# Edit docker-compose.yml and set EMAIL_CHECK_INTERVAL_MINUTES
```

### Without Docker

Run the scheduler manually:

```bash
# Run in background with default 60-minute interval
python email_scheduler.py &

# Or set custom interval (in minutes)
EMAIL_CHECK_INTERVAL_MINUTES=30 python email_scheduler.py &

# View logs
tail -f logs/email_scheduler.log
```

### Setup Gmail OAuth

Before email checking works, you need to authenticate:

```bash
# With Docker
docker-compose run --rm app python cli.py email-check --setup

# Without Docker
python cli.py email-check --setup
```

Follow the instructions in [GMAIL_SETUP.md](GMAIL_SETUP.md) for obtaining credentials.

## Production Deployment

### Backend

**With Docker:**
```bash
# Use docker-compose for production
docker-compose -f docker-compose.yml up -d

# Or deploy to cloud platforms
# AWS ECS, Google Cloud Run, Azure Container Instances, etc.
```

**Without Docker:**
```bash
# Install production dependencies
pip install -r requirements.txt

# Run with gunicorn (production)
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker
```

See [DOCKER.md](DOCKER.md) for detailed production deployment guide.

### Frontend

```bash
cd dashboard
npm run build
# Serve the dist/ folder with your preferred static server
```

## Screenshots

### Applications View
![Applications Table](https://github.com/user-attachments/assets/8382b8ba-03a5-4350-8859-021183e1f0e2)

### Add Application Form
![Add Application](https://github.com/user-attachments/assets/4eef2c0e-f0d4-45c9-9a51-6aba2c54701f)

### Analytics Dashboard
![Analytics](https://github.com/user-attachments/assets/65183099-8770-407e-9339-2b76979f2527)

## Troubleshooting

### CORS Issues
The API is configured to allow requests from `localhost:3000` and `localhost:5173`. If using a different port, update the `allow_origins` in `api.py`.

### Database Issues
If you encounter database errors, delete `job_tracker.db` and run `python init_db.py` again.

### Port Conflicts
- Backend default: 8000
- Frontend default: 5173

Change ports in startup commands if needed.
