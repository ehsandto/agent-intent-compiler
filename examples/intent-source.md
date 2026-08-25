# Production database migration intent

Goal: migrate the production database to the new managed cluster.

Constraints: no data loss; no unplanned downtime; preserve encryption and access controls.

Forbidden action: never delete or decommission the source database before backup restoration, integrity, security, and service-health checks pass.
