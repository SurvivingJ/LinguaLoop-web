# Row Level Security (RLS) Policies

**Purpose**: Document the Row Level Security configuration and dual-client pattern used for data access control in LinguaLoop/LinguaDojo.

---

## Overview

The application uses a **dual Supabase client pattern** to balance security with operational needs:
- **Anon Client**: RLS-enforced client for user-facing operations
- **Service Role Client**: Bypasses RLS for administrative operations

This pattern is implemented through the `SupabaseFactory` singleton.

**Source**: `services/supabase_factory.py:1-99`

---

## Dual Client Pattern

### Anon Client (RLS-Enforced)

**Purpose**: User-facing operations that should respect row-level permissions.

**Key**: `SUPABASE_ANON_KEY` (read from environment)

**Usage**:
```python
supabase = SupabaseFactory.get_anon_client()
# OR
supabase = get_supabase()
```

**Applied in**:
- User authentication flows (`routes/auth.py`)
- User profile queries
- Test browsing (public read access)
- Test submission (user can only submit for themselves)
- User-specific data queries (elo_ratings, test_results, token balance)

**RLS Enforcement**: The anon key ensures users can only:
- Read their own `user_elo_ratings`, `test_results`, `user_tokens`
- Read public `tests` and `questions` data
- Insert their own `test_results`
- Cannot read other users' private data

---

### Service Role Client (Bypasses RLS)

**Purpose**: Administrative and system operations that require full database access.

**Key**: `SUPABASE_SERVICE_ROLE_KEY` (read from environment)

**Usage**:
```python
supabase = SupabaseFactory.get_service_client()
# OR
supabase = get_supabase_admin()
```

**Applied in**:
- **AI Pipelines**: Test generation and topic generation orchestrators need unrestricted access to insert generated content
- **Batch Scripts**: `upload_tests_to_supabase.py`, `backfill_test_skill_ratings.py`
- **Background Jobs**: Scripts that run outside user context
- **Administrative Operations**: Bulk inserts, backfills, migrations

**Why Bypass RLS**:
- Pipelines insert tests on behalf of system/gen_user, not the current authenticated user
- Batch operations need to read/write across all user data
- Background jobs have no authenticated user context

**Source**: `services/supabase_factory.py:50-67`

---

## Expected RLS Policies

While RLS policies are managed directly in Supabase (not in codebase), the application expects the following policy structure:

### Users Table
- **Read**: Users can read their own profile
- **Update**: Users can update their own profile
- **Managed by**: Supabase Auth (automatic RLS)

### Test Results
- **Insert**: Authenticated users can insert their own test results
- **Read**: Users can only read their own test results
- **Update**: No updates allowed (immutable records)

### User ELO Ratings
- **Read**: Users can read their own ELO ratings
- **Update**: Only via RPC function `process_test_submission` (server-side update)

### User Tokens
- **Read**: Users can read their own token balance
- **Update**: Only via payment webhook or RPC (server-side update)

### Tests & Questions
- **Read**: Public read access (all authenticated users can browse tests)
- **Insert**: Service role only (via pipelines)
- **Update**: Service role only

### Topics
- **Read**: Public read access
- **Insert**: Service role only (via topic generation pipeline)

### Reports
- **Insert**: Authenticated users can insert reports
- **Read**: Service role only (admin access)

---

## Security Considerations

### 1. Key Protection
- **Service Role Key**: Must NEVER be exposed to client-side code. Only used in backend routes and scripts.
- **Anon Key**: Safe to expose in frontend (RLS policies protect data).

### 2. Authentication vs. Authorization
- **Authentication**: Handled by JWT middleware (`@jwt_required` decorator)
- **Authorization**: Enforced by RLS policies (user can only access own data)

**Source**: `middleware/auth.py:1-281`

### 3. RPC Functions
RPC functions like `process_test_submission` run with the caller's privileges (RLS still applies) unless explicitly using service role client.

**Source**: `migrations/process_test_submission_v2.sql`

### 4. API Routes Pattern
```python
@tests_bp.route('/<slug>/submit', methods=['POST'])
@jwt_required  # Ensures user is authenticated
def submit_test(slug):
    user_id = g.current_user_id  # From JWT
    supabase = get_supabase()  # Anon client (RLS enforced)

    # RLS ensures user can only insert for themselves
    result = supabase.rpc('process_test_submission', {
        'p_user_id': user_id,  # Must match JWT user
        # ...
    }).execute()
```

---

## RLS Bypass Scenarios

### Safe Bypass (Service Role)
- **Test Generation Pipeline**: Inserts tests and questions on behalf of system
- **Topic Generation Pipeline**: Inserts topics with embeddings
- **Batch Uploads**: Administrative bulk insert operations
- **Backfill Scripts**: Adding missing data (e.g., `backfill_test_skill_ratings.py`)

### Unsafe Bypass (Avoided)
- Never use service role client in user-facing API routes
- Never pass service role key to frontend
- Never bypass RLS for user data queries in routes

---

## RLS Policy Management

**Location**: Supabase Dashboard > Authentication > Policies

**Policy Creation**: Policies are created manually in Supabase UI or via SQL in migrations.

**No ORM**: The application doesn't use an ORM like SQLAlchemy, so RLS policies are the primary authorization mechanism.

---

## Verification

To verify RLS is working:

1. **Test with Anon Client**: Try to read another user's test results → should fail
2. **Test with Service Role**: Same query → should succeed
3. **Check Policy**: In Supabase dashboard, view policies on each table

---

## Related Documents

- [Supabase Factory](../04-Backend/05-services/01-supabase-factory.md)
- [Auth Middleware](../04-Backend/04-middleware/01-auth-middleware.md)
- [RPC Functions](./04-rpc-functions.md)
- [Security Model](../02-Architecture/06-security-model.md)
- [Tables Reference](./02-tables-reference.md)
