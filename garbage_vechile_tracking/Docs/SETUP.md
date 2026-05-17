# 🚀 Quick Setup Guide

This guide will help you set up and run the Garbage Vehicle Tracking System in minutes.

## Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.8+** ([Download](https://www.python.org/downloads/))
- **Node.js 16+** ([Download](https://nodejs.org/))
- **npm** (comes with Node.js) or **bun**
- **Git** ([Download](https://git-scm.com/downloads))

## 🔧 Quick Start

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd garbage_vechile_tracking
```

### Step 2: Backend Setup (5 minutes)

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   
   The default values work for local development. No changes needed!

5. **Initialize database with Pune city data:**
   ```bash
   python init_db.py
   ```
   
   You should see:
   ```
   ✅ Created 4 zones
   ✅ Created 10 wards
   ✅ Created 3 vendors
   ✅ Created 11 drivers
   ✅ Created 9 routes
   ✅ Created 11 trucks
   ✅ Created 6 pickup points
   ✅ Created 2 alerts
   🎉 Database initialization completed successfully!
   ```

6. **Start the backend server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   You should see:
   ```
   🚛 Vehicle simulation started
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

7. **Verify backend is running:**
   
   Open http://localhost:8000/docs in your browser. You should see the API documentation.

### Step 3: Frontend Setup (3 minutes)

**Open a NEW terminal** (keep backend running in the first terminal)

1. **Navigate to project root:**
   ```bash
   cd /path/to/garbage_vechile_tracking
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   
   The default values point to localhost:8000. Perfect for development!

4. **Start the development server:**
   ```bash
   npm run dev
   ```
   
   You should see:
   ```
   VITE v5.x.x  ready in xxx ms
   ➜  Local:   http://localhost:5173/
   ```

5. **Open the application:**
   
   Navigate to http://localhost:5173 in your browser.

## ✅ Verify Everything is Working

### Backend Health Check

```bash
curl http://localhost:8000/health
```
Expected response: `{"status":"healthy"}`

### Check Live Trucks

```bash
curl http://localhost:8000/api/trucks/live
```
You should see JSON data for 11 trucks with live GPS coordinates.

### Frontend

Open http://localhost:5173 and you should see:
- Live map with moving vehicles
- Fleet statistics showing 11 trucks
- Active alerts
- Real-time updates every 5 seconds

## 🎯 What You Should See

### Backend (Terminal 1)
```
🚛 Vehicle simulation started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Frontend (Terminal 2)
```
VITE v5.x.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### Browser
- Dashboard with live vehicle tracking map
- 11 vehicles shown on map (some moving, some idle)
- Fleet statistics: 11 total trucks, X active, X idle
- Active alerts panel
- Real-time position updates

## 🔄 Daily Usage

Once set up, to run the application:

**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
npm run dev
```

## 📊 System Overview

### What's Included Out of the Box:

**Data:**
- ✅ 4 Zones (North, South, East, West)
- ✅ 10 Wards distributed across zones
- ✅ 3 Vendors (Mahesh Enterprises, Green Transport Co, City Waste Solutions)
- ✅ 11 Trucks (9 regular + 2 spare)
- ✅ 11 Drivers
- ✅ 9 Collection Routes
- ✅ 6 Pickup Points
- ✅ 2 Active Alerts

**Features:**
- ✅ Live GPS tracking simulation
- ✅ Real-time WebSocket updates
- ✅ Vehicle status monitoring
- ✅ Alert management
- ✅ Reports and analytics
- ✅ Zone and vendor performance metrics

## 🐛 Troubleshooting

### Backend Won't Start

**Error: "Module not found"**
```bash
# Make sure you activated the virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Port 8000 is already in use"**
```bash
# Find and kill the process using port 8000
# On macOS/Linux:
lsof -ti:8000 | xargs kill -9

# On Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Frontend Won't Start

**Error: "Cannot find module"**
```bash
# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Error: "Port 5173 is already in use"**
```bash
# The dev server will automatically try the next available port
# Or kill the process:
# On macOS/Linux:
lsof -ti:5173 | xargs kill -9
```

### No Live Data on Map

1. **Check backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check WebSocket connection:**
   - Open browser console (F12)
   - Look for "WebSocket connected" message
   - If not, check that backend is running

3. **Verify data exists:**
   ```bash
   curl http://localhost:8000/api/trucks/live
   ```
   Should return array of trucks.

### Database Issues

**Reset database:**
```bash
cd backend
rm -f garbage_tracking.db  # Delete existing database
python init_db.py           # Recreate with fresh data
```

## 📚 Next Steps

After successful setup:

1. **Explore the API:** http://localhost:8000/docs
2. **View live trucks:** http://localhost:5173
3. **Check reports:** Navigate to Reports page in the UI
4. **View alerts:** Check the Alerts page
5. **Explore zones:** Navigate to Master → Zones & Wards

## 🎓 Understanding the System

### Vehicle Simulation

The backend automatically simulates realistic vehicle movement:
- Trucks move within their assigned zone boundaries
- Speed varies between 15-40 km/h when moving
- Status changes: moving → dumping → idle → moving
- GPS coordinates updated every 5 seconds
- Data broadcast via WebSocket to all connected clients

### Data Flow

```
1. Backend initializes → Creates 11 trucks in database
2. Vehicle simulator starts → Moves trucks every 5 seconds
3. Database updated → New positions saved
4. WebSocket broadcasts → Sends updates to frontend
5. Frontend receives → Updates map markers in real-time
```

## 💡 Tips

1. **Keep both terminals open** - You need both backend and frontend running
2. **Check API docs** - Visit http://localhost:8000/docs for full API reference
3. **Browser console** - Press F12 to see real-time update logs
4. **Network tab** - Use browser DevTools to see WebSocket messages
5. **Multiple tabs** - Open multiple browser tabs to see synchronized updates

## 🎉 Success!

If you see:
- ✅ Backend running on port 8000
- ✅ Frontend running on port 5173
- ✅ Map with moving vehicles
- ✅ Live statistics updating

**Congratulations! You're all set up!** 🎊

## 📞 Need Help?

- Check the main [PROJECT_README.md](./PROJECT_README.md) for detailed documentation
- Review the [backend README](./backend/README.md) for API details
- Open an issue if you encounter problems

---

**Pro Tip:** Bookmark http://localhost:8000/docs for quick API reference while developing!
