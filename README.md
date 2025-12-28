# Automation Dashboard Backend

FastAPI-based backend for the RPA Automation Dashboard providing real-time metrics via WebSocket.

## 📋 Overview

This backend provides real-time dashboard data for monitoring RPA (Robotic Process Automation) transactions, VM utilization, and process queues.

## 🛠 Tech Stack

- **Framework**: FastAPI
- **Database**: SQL Server
- **ORM**: SQLAlchemy
- **WebSocket**: Native FastAPI WebSocket support
- **Python Version**: 3.10+

## 📁 Project Structure
```
automation-fastapi-service/
├── app/
│   ├── main.py                 # FastAPI application & WebSocket endpoint
│   ├── api/
│   │   └── routes.py          # API routes (if needed)
│   ├── database/
│   │   ├── connection.py      # Database connection config
│   │   └── queries.py         # Database query functions
│   ├── models/
│   │   └── models.py          # SQLAlchemy ORM models
│   └── schemas/               # Pydantic schemas (future use)
├── myenv/                     # Virtual environment
├── .env                       # Environment variables (credentials)
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🚀 Setup Instructions

### 1. Prerequisites

- Python 3.10 or higher
- SQL Server (local or remote)
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/roshanvrio/automation-fastapi-service.git
cd automation-fastapi-service
```

### 3. Create Virtual Environment
```bash
python -m venv myenv
```

### 4. Activate Virtual Environment

**Windows:**
```bash
.\myenv\Scripts\Activate
```

**Mac/Linux:**
```bash
source myenv/bin/activate
```

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables

Create a `.env` file in the root directory:
```env
DB_SERVER=.
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_NAME=DashboardDB
```

### 7. Database Setup

Ensure you have:
- `DashboardDB` database created
- `process_transactions` table with data
- `vm_pool` table with VM list

### 8. Run the Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at: `http://localhost:8000`

## 🔌 WebSocket Endpoint

### `/ws/dashboard`

Real-time dashboard data endpoint that sends updates every 2 seconds.

**Connection:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/dashboard');
```

**Message Types:**

1. **metrics_update**
```json
{
  "type": "metrics_update",
  "data": {
    "exceptions": 10,
    "successful": 150,
    "totalInQueue": 25,
    "errors": 5,
    "avgTime": 125
  }
}
```

2. **queue_priority_update**
```json
{
  "type": "queue_priority_update",
  "data": [
    {
      "processName": "QC_RPA_PTP",
      "triggerIndication": "Email",
      "inQueueCount": 5,
      "totalCount": 29,
      "rpaTool": "UiPath"
    }
  ]
}
```

3. **active_vms_update**
```json
{
  "type": "active_vms_update",
  "data": [
    {
      "machineName": "VM33.BOT",
      "processName": "QC_RPA_PTP",
      "triggerIndication": "Email",
      "completedTransactions": 120,
      "lastRunTime": "3.5 Hours",
      "rpaTool": "UiPath",
      "successfulCount": 115,
      "failedCount": 5
    }
  ]
}
```

4. **idle_vms_update**
```json
{
  "type": "idle_vms_update",
  "data": ["VM1", "VM2", "VM5", "VM10"]
}
```

5. **vm_utilization_update**
```json
{
  "type": "vm_utilization_update",
  "data": {
    "vmUtilization": [
      {
        "vmName": "VM15",
        "completedTransactions": 200,
        "utilizationHours": 18.5
      }
    ],
    "topPerformer": {
      "vmName": "VM15",
      "utilizationHours": 18.5
    }
  }
}
```

## 📊 Database Schema

### process_transactions
Main table storing RPA transaction data.

Key columns:
- `ProcessTransactionId` (Primary Key)
- `ProcessName`, `ProcessStatus`, `CaseStatus`
- `MachineName`, `StartTime`, `EndTime`
- `CreatedDate`, `RPATool`

### vm_pool
VM availability table.

Columns:
- `Automation Anywhere VMs`
- `Uipath VMs`

## 🔧 Development

### Adding New Query Functions

1. Add function to `app/database/queries.py`
2. Import in `app/main.py`
3. Add to WebSocket loop
4. Update README with new message type

### Testing

Start backend and connect frontend:

**Backend:**
```bash
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd ../automation-react-service
npm start
```

## 🌐 CORS Configuration

Configured for:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)

To add more origins, update `app/main.py`:
```python
allow_origins=["http://localhost:3000", "http://your-origin:port"]
```

## 📝 Notes

- Dashboard displays **current date data only**
- WebSocket sends updates every 2 seconds
- All datetime fields filter by `CreatedDate`
- VM names in database use `.BOT` suffix, frontend displays without

## 👥 Contributing

1. Create a new branch: `git checkout -b feature-name`
2. Make changes and commit: `git commit -m "Description"`
3. Push to branch: `git push origin feature-name`
4. Create Pull Request

## 📄 License

Internal project for [Company Name]

## 🆘 Troubleshooting

**WebSocket won't connect:**
- Check backend is running on port 8000
- Verify CORS origins include frontend URL

**No data showing:**
- Verify database connection in `.env`
- Check `CreatedDate` has today's data
- Check console logs for errors

**Import errors:**
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

---

**Created by:** Sai Charan  
**Date:** December 2025  
**Branch:** Dashboard_Backend