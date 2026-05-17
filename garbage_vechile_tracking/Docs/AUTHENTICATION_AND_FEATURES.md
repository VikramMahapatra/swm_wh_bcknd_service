# Authentication, Tickets, Social Media, and Analytics - Implementation Guide

## Overview

This document describes the newly implemented authentication system, tickets management, social media monitoring, and analytics features for the Garbage Vehicle Tracking System.

---

## 🔐 Authentication System

### Features
- JWT token-based authentication
- Role-based access control (Admin/User)
- User registration and login
- Secure password hashing with bcrypt
- OAuth2 password flow support

### API Endpoints

#### 1. Register New User
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe",
  "role": "user"  // or "admin"
}
```

**Response:**
```json
{
  "id": "user-3",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2026-02-10T20:00:00"
}
```

#### 2. Login (JSON)
```http
POST /api/auth/login-json
Content-Type: application/json

{
  "email": "admin@city.gov",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user-1",
    "email": "admin@city.gov",
    "name": "Admin User",
    "role": "admin",
    "is_active": true
  }
}
```

#### 3. Login (Form Data)
```http
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin@city.gov&password=admin123
```

#### 4. Get Current User
```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

#### 5. List All Users (Admin Only)
```http
GET /api/auth/users
Authorization: Bearer {admin_access_token}
```

### Default Credentials

**Admin Account:**
- Email: `admin@city.gov`
- Password: `admin123`
- Role: `admin`

**Operator Account:**
- Email: `operator@city.gov`
- Password: `operator123`
- Role: `user`

---

## 🎫 Tickets Management System

### Features
- Create and manage support tickets
- Multiple categories (complaint, request, feedback, query)
- Priority levels (low, medium, high, critical)
- Status workflow (open → in_progress → pending → resolved → closed)
- Comments and discussions
- SLA tracking
- Assignment management

### API Endpoints

#### 1. List All Tickets
```http
GET /api/tickets/
GET /api/tickets/?status=open
GET /api/tickets/?priority=high
GET /api/tickets/?category=complaint
GET /api/tickets/?zone_id=ZN001
```

**Response:**
```json
[
  {
    "id": "ticket-1",
    "ticket_number": "TKT-000001",
    "title": "Garbage not collected in Kharadi Sector 5",
    "description": "Residents reporting that garbage has not been collected for 2 days",
    "category": "complaint",
    "priority": "high",
    "status": "open",
    "reporter_name": "Ramesh Kumar",
    "reporter_phone": "+91 9876543210",
    "reporter_email": "ramesh@example.com",
    "location": "Kharadi, Sector 5",
    "zone_id": "ZN003",
    "ward_id": "WD006",
    "assigned_to": null,
    "created_at": "2026-02-10T20:00:00",
    "due_date": "2026-02-11T20:00:00",
    "sla_breached": false
  }
]
```

#### 2. Get Single Ticket
```http
GET /api/tickets/{ticket_id}
```

#### 3. Create Ticket
```http
POST /api/tickets/
Content-Type: application/json

{
  "title": "New complaint",
  "description": "Description of the issue",
  "category": "complaint",
  "priority": "medium",
  "reporter_name": "John Doe",
  "reporter_phone": "+91 9876543210",
  "reporter_email": "john@example.com",
  "location": "Kharadi",
  "zone_id": "ZN003",
  "ward_id": "WD006"
}
```

#### 4. Update Ticket
```http
PUT /api/tickets/{ticket_id}
Content-Type: application/json

{
  "status": "in_progress",
  "assigned_to": "user-1",
  "priority": "high"
}
```

#### 5. Get Ticket Comments
```http
GET /api/tickets/{ticket_id}/comments
```

#### 6. Add Comment
```http
POST /api/tickets/{ticket_id}/comments
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "comment": "We're looking into this issue",
  "is_internal": false
}
```

#### 7. Ticket Statistics
```http
GET /api/tickets/statistics/summary
```

**Response:**
```json
{
  "total_tickets": 3,
  "open_tickets": 1,
  "in_progress": 1,
  "resolved": 1,
  "closed": 0,
  "high_priority_open": 1
}
```

---

## 🐦 Social Media Monitoring (Twitter)

### Features
- Track Twitter mentions
- Sentiment analysis (positive, negative, neutral)
- Category classification (complaint, appreciation, query, suggestion)
- Response management
- Location tracking
- Statistics and analytics

### API Endpoints

#### 1. List Twitter Mentions
```http
GET /api/social-media/twitter-mentions
GET /api/social-media/twitter-mentions?sentiment=negative
GET /api/social-media/twitter-mentions?category=complaint
GET /api/social-media/twitter-mentions?is_responded=false
```

**Response:**
```json
[
  {
    "id": "mention-1",
    "tweet_id": "1234567890",
    "author": "@citizen_pune",
    "author_name": "Pune Citizen",
    "content": "@MunicipalGC Garbage truck hasn't arrived...",
    "timestamp": "2026-02-10T18:00:00",
    "likes": 45,
    "retweets": 12,
    "replies": 8,
    "sentiment": "negative",
    "category": "complaint",
    "location": "Kharadi, Sector 5",
    "is_responded": false,
    "response_text": null,
    "response_at": null
  }
]
```

#### 2. Get Single Mention
```http
GET /api/social-media/twitter-mentions/{mention_id}
```

#### 3. Create Twitter Mention
```http
POST /api/social-media/twitter-mentions
Content-Type: application/json

{
  "tweet_id": "1234567893",
  "author": "@user_pune",
  "author_name": "Pune User",
  "content": "Tweet content here",
  "timestamp": "2026-02-10T20:00:00",
  "likes": 10,
  "retweets": 2,
  "replies": 1,
  "sentiment": "neutral",
  "category": "query",
  "location": "Pune"
}
```

#### 4. Respond to Mention
```http
PUT /api/social-media/twitter-mentions/{mention_id}/respond
Content-Type: application/json

{
  "response_text": "Thank you for bringing this to our attention. We're looking into it."
}
```

#### 5. Twitter Statistics
```http
GET /api/social-media/twitter-mentions/statistics/summary
```

**Response:**
```json
{
  "total_mentions": 3,
  "responded": 1,
  "pending_response": 2,
  "positive_sentiment": 1,
  "negative_sentiment": 1,
  "neutral_sentiment": 1,
  "complaints": 1,
  "appreciation": 1
}
```

---

## 📊 Analytics & Reporting

### Features
- Performance overview
- Zone-wise metrics
- Vendor-wise metrics
- Maintenance predictions
- Collection rate trends
- Custom analytics storage

### API Endpoints

#### 1. Performance Overview
```http
GET /api/analytics/performance/overview
```

**Response:**
```json
{
  "collection_efficiency": 69.57,
  "total_trucks": 10,
  "active_trucks": 7,
  "idle_trucks": 3,
  "active_alerts": 2,
  "total_trips_completed": 32,
  "total_trips_allowed": 46
}
```

#### 2. Zone-wise Performance
```http
GET /api/analytics/performance/zone-wise
```

**Response:**
```json
[
  {
    "zone_id": "ZN003",
    "zone_name": "East Zone",
    "total_trucks": 4,
    "active_trucks": 3,
    "total_trips_completed": 14,
    "collection_efficiency": 70.0
  }
]
```

#### 3. Vendor-wise Performance
```http
GET /api/analytics/performance/vendor-wise
```

**Response:**
```json
[
  {
    "vendor_id": "VND001",
    "vendor_name": "Mahesh Enterprises",
    "total_trucks": 4,
    "active_trucks": 3,
    "total_trips_completed": 15,
    "collection_efficiency": 75.0
  }
]
```

#### 4. Maintenance Predictions
```http
GET /api/analytics/predictions/maintenance
```

**Response:**
```json
[
  {
    "truck_id": "TRK001",
    "registration_number": "MH-12-AB-1234",
    "trips_completed": 5,
    "trips_allowed": 5,
    "utilization": 100.0,
    "recommendation": "Schedule maintenance soon - high utilization"
  }
]
```

#### 5. Collection Rate Trends
```http
GET /api/analytics/trends/collection-rate
```

**Response:**
```json
[
  {
    "zone_id": "ZN003",
    "zone_name": "East Zone",
    "total_pickup_points": 120,
    "collection_rate": 92,
    "trend": "improving"
  }
]
```

#### 6. Store Custom Analytics
```http
POST /api/analytics/
Content-Type: application/json

{
  "date": "2026-02-10T20:00:00",
  "metric_name": "avg_collection_time",
  "metric_value": 125.5,
  "metric_type": "performance",
  "zone_id": "ZN003",
  "additional_data": "{\"unit\": \"minutes\"}"
}
```

---

## 🔗 Frontend Integration

### Using the API Service

The frontend API service has been updated with methods for all new endpoints:

```typescript
import { apiService } from '@/services/api';

// Authentication
const response = await apiService.login('admin@city.gov', 'admin123');
const token = response.access_token;
const user = response.user;

// Tickets
const tickets = await apiService.getTickets({ status: 'open' });
const newTicket = await apiService.createTicket(ticketData);
const stats = await apiService.getTicketStatistics();

// Twitter
const mentions = await apiService.getTwitterMentions({ sentiment: 'negative' });
const twitterStats = await apiService.getTwitterStatistics();

// Analytics
const overview = await apiService.getPerformanceOverview();
const zonePerf = await apiService.getZoneWisePerformance();
const predictions = await apiService.getMaintenancePredictions();
```

---

## 📝 Database Schema

### Users Table
- `id`: User ID (primary key)
- `email`: Email (unique)
- `name`: User name
- `hashed_password`: Password hash
- `role`: User role (admin/user)
- `is_active`: Account status
- `created_at`: Creation timestamp
- `last_login`: Last login timestamp

### Tickets Table
- `id`: Ticket ID (primary key)
- `ticket_number`: Unique ticket number (TKT-000001)
- `title`: Ticket title
- `description`: Detailed description
- `category`: Type (complaint, request, feedback, query)
- `priority`: Priority level (low, medium, high, critical)
- `status`: Current status
- `reporter_*`: Reporter information
- `location`, `zone_id`, `ward_id`: Location details
- `assigned_to`: Assigned user ID
- `created_at`, `updated_at`, `resolved_at`: Timestamps
- `due_date`: Due date
- `sla_breached`: SLA breach flag

### Twitter Mentions Table
- `id`: Mention ID (primary key)
- `tweet_id`: Unique tweet ID
- `author`, `author_name`: Tweet author
- `content`: Tweet content
- `timestamp`: Tweet timestamp
- `likes`, `retweets`, `replies`: Engagement metrics
- `sentiment`: Sentiment analysis result
- `category`: Category classification
- `location`: Location mentioned
- `is_responded`: Response status
- `response_text`, `response_at`: Response details

### Analytics Table
- `id`: Analytics ID (primary key)
- `date`: Data point date
- `metric_name`: Name of the metric
- `metric_value`: Numeric value
- `metric_type`: Type (performance, efficiency, etc.)
- `zone_id`, `vendor_id`: Optional associations
- `additional_data`: JSON string for extra data

---

## 🧪 Testing the New Features

### 1. Test Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login-json \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@city.gov","password":"admin123"}'

# Get current user (use token from login)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Test Tickets
```bash
# List tickets
curl http://localhost:8000/api/tickets/

# Get statistics
curl http://localhost:8000/api/tickets/statistics/summary

# Create ticket
curl -X POST http://localhost:8000/api/tickets/ \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","category":"complaint","priority":"medium"}'
```

### 3. Test Social Media
```bash
# List mentions
curl http://localhost:8000/api/social-media/twitter-mentions

# Get statistics
curl http://localhost:8000/api/social-media/twitter-mentions/statistics/summary
```

### 4. Test Analytics
```bash
# Performance overview
curl http://localhost:8000/api/analytics/performance/overview

# Zone-wise performance
curl http://localhost:8000/api/analytics/performance/zone-wise

# Maintenance predictions
curl http://localhost:8000/api/analytics/predictions/maintenance
```

---

## 📖 API Documentation

All endpoints are automatically documented with Swagger UI at:
```
http://localhost:8000/docs
```

Interactive API testing is available through the Swagger interface.

---

## 🔒 Security Notes

1. **Password Hashing**: User passwords are hashed using bcrypt (currently in mock mode for compatibility)
2. **JWT Tokens**: Access tokens expire after 30 minutes
3. **Role-Based Access**: Certain endpoints require admin role
4. **CORS**: Currently allows all origins (restrict in production)
5. **HTTPS**: Use HTTPS in production environments

---

## 🚀 Next Steps

1. Update frontend components to use the new API endpoints
2. Implement real-time updates for tickets via WebSocket
3. Add email notifications for ticket updates
4. Integrate actual Twitter API for live mentions
5. Implement PDF export for reports
6. Add more predictive analytics models

---

## 📞 Support

For questions or issues, refer to:
- Main API docs: `http://localhost:8000/docs`
- Project README: `PROJECT_README.md`
- Setup guide: `SETUP.md`
