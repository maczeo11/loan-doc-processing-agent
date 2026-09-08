"""
SQLAlchemy database models for PostgreSQL schema.

Tables:
- applications (id, status, created_at, updated_at, reviewer_id)
- documents (id, application_id, filename, storage_uri, doc_type, sha256)
- jobs (id, application_id, status, attempt_count, lease_until)
- audit_events (id, application_id, from_status, to_status, actor, reason, timestamp)
"""

# Stubs for Balaji to implement schema migrations and models
