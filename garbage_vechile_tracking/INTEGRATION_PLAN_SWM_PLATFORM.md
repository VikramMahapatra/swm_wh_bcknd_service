# SWM Platform Integration Plan: garbage_vechile_tracking Frontend

## 1. API Endpoint Mapping
- Review all API calls in src/services/api.ts, hooks, and components.
- Map legacy endpoints to new swm-platform compatibility endpoints.
- Document mapping in a spreadsheet for tracking.

## 2. Environment Configuration
- In .env, set:
  VITE_API_URL=http://localhost:8003
  VITE_SWM_ADMIN_API_URL=http://localhost:8003
- Ensure all API calls use these variables (via config/api.ts).

## 3. Proxy Setup (Optional for Dev)
- In vite.config.ts, add server.proxy if CORS issues occur:
  server: {
    proxy: {
      '/api': 'http://localhost:8003',
    },
  },

## 4. Contract Validation
- For each UI module (auth, drivers, trucks, tickets, reports, analytics, etc.):
  - Test UI against new endpoints.
  - Patch minor contract mismatches in backend if needed.

## 5. Authentication
- Ensure login, token refresh, and user info use swm-platform endpoints.
- Test protected routes and role-based UI features.

## 6. Error Handling
- Validate error messages and status codes in the UI.
- Test empty states, 401/403/404/500 errors, and form validation.

## 7. End-to-End Testing
- Run through all major UI workflows.
- Use contract tests and manual QA.

## 8. Deployment
- Deploy backend and frontend to staging.
- Monitor logs and user feedback.
- Prepare rollback plan if needed.

---

**Next Steps:**
- Update .env and config/api.ts to point to swm-platform.
- Test each UI module against the new backend.
- Track and fix any contract mismatches.
