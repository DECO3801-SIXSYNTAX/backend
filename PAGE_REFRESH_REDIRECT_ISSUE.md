# Page Refresh Redirect Issue - SOLVED

## Problem
When you refresh the page on `/planner` routes, it redirects to `/admin`.

## Root Cause
You're logged in as **`admin@test.com`** with role **`admin`**, but trying to access `/planner` routes which are protected by `PlannerOnly` guard.

### What's Happening:
```
1. Page loads → DashboardContext restores user from localStorage
2. User role: 'admin'
3. You're on /planner route
4. RoleGuard checks: Is 'admin' allowed on /planner? NO
5. RoleGuard redirects: if (userRole === 'admin') return <Navigate to="/admin" />
6. You get redirected to /admin
```

### Code Flow (App.tsx line 100-106):
```typescript
if (allowedRoles.length > 0 && !allowedRoles.includes(userRole)) {
  console.log('Role not allowed, redirecting to correct dashboard');
  // Redirect to their appropriate dashboard
  if (userRole === 'admin') return <Navigate to="/admin" replace />;  // ← YOU ARE HERE
  if (userRole === 'planner') return <Navigate to="/planner" replace />;
  if (userRole === 'vendor') return <Navigate to="/vendor" replace />;
  return <Navigate to="/signin" replace />;
}
```

---

## Solution Options

### Option 1: Login with a Planner Account (RECOMMENDED)

1. **Logout from admin account**:
```typescript
// In browser console:
localStorage.clear();
// Then refresh page
```

2. **Register a new planner account**:
   - Go to: http://localhost:3000/signup
   - Email: yourname@example.com (NOT admin@test.com)
   - Password: yourpassword123
   - Role: **Event Planner** ← Important!
   - Fill in company, phone, experience, specialty
   - Click "Create Account"

3. **Login with planner account**:
   - Go to: http://localhost:3000/signin
   - Email: yourname@example.com
   - Password: yourpassword123
   - You'll be redirected to /planner (and won't be redirected on refresh!)

---

### Option 2: Create Admin Dashboard Pages

If you want to access `/admin` routes with your admin account, create these pages:

**Missing Admin Routes**:
- `/admin` → AdminDashboard
- `/admin/events` → ViewEvents
- `/admin/users` → ManageUsers
- `/admin/event-overview` → EventOverview

These routes exist in your `App.tsx` but may need proper content.

---

### Option 3: Make Admin Access All Routes (NOT RECOMMENDED)

You could modify `RoleGuard` to allow admins on all routes, but this breaks role-based security:

```typescript
// App.tsx - RoleGuard function
if (allowedRoles.length > 0 && !allowedRoles.includes(userRole)) {
  // Allow admin to access all routes (NOT SECURE)
  if (userRole === 'admin') {
    console.log('Admin accessing non-admin route');
    return <>{children}</>;  // Allow access
  }
  
  // Redirect others
  if (userRole === 'planner') return <Navigate to="/planner" replace />;
  if (userRole === 'vendor') return <Navigate to="/vendor" replace />;
  return <Navigate to="/signin" replace />;
}
```

**Warning**: This defeats the purpose of role-based access control.

---

## Quick Fix Commands

### Check Current User:
```javascript
// In browser console (F12)
const user = JSON.parse(localStorage.getItem('user'));
console.log('Current user:', user);
console.log('Role:', user?.role);
console.log('Email:', user?.email);
```

### Logout and Clear Session:
```javascript
// In browser console
localStorage.clear();
window.location.href = '/signin';
```

### Check Available Django Users:
You already have these Django users:
```
1. admin@test.com - role: admin
2. teukuauli18@gmail.com - role: guest
```

You need to register a **planner** account!

---

## Recommended Solution

**Register a new planner account**:

1. Open browser
2. Go to: http://localhost:3000/signup
3. Fill form:
   - Email: planner@example.com
   - Password: planner123
   - Name: Test Planner
   - Role: **Event Planner** ← SELECT THIS
   - Company: Test Company
   - Phone: +1234567890
   - Experience: 3-5 years
   - Specialty: Corporate Events
4. Click "Create Account"
5. Login with planner@example.com / planner123
6. You'll be on /planner dashboard
7. Refresh page → Stays on /planner (no redirect!)

---

## Why This Happens

### Role-Based Routing:
- `/admin/*` routes → Requires `role: 'admin'`
- `/planner/*` routes → Requires `role: 'planner'`
- `/vendor/*` routes → Requires `role: 'vendor'`

### Guards Enforce This:
```typescript
<Route path="/planner/*" element={<PlannerOnly>...</PlannerOnly>} />
```

`PlannerOnly` = `RoleGuard` with `allowedRoles=['planner']`

If your user role is `'admin'`, you get redirected from `/planner` to `/admin`.

---

## Verify After Login

After logging in with a planner account:

1. **Check localStorage**:
```javascript
const user = JSON.parse(localStorage.getItem('user'));
console.log(user.role);  // Should be 'planner'
```

2. **Try refresh**:
   - Press F5 on /planner page
   - Should stay on /planner (no redirect!)

3. **Navigate to different routes**:
   - /planner/events
   - /planner/guest-management
   - /planner/event-settings
   - All should work without redirecting

---

## Summary

**Problem**: Admin user can't access /planner routes
**Cause**: Role-based guards redirect admin → /admin
**Solution**: Register and login with a planner account

**Steps**:
1. Logout (clear localStorage)
2. Register planner account at /signup
3. Login with planner credentials
4. Access /planner routes without redirect
5. Refresh works correctly!

**Alternative**: Use admin routes at `/admin` with your admin account
