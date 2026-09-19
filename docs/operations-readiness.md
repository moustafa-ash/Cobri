# Vendor-neutral operational procedures

## Credential rotation

Create a replacement credential in the provider's approved console, update the secret store for the target environment, deploy/restart one worker, verify a synthetic health/evaluation check, then revoke the old credential. Never paste credentials into logs, issues, or learner data. If verification fails, restore the prior secret and investigate before revocation.

## Incidents and alerts

Page the named service owner on readiness loss, repeated worker failures/stale leases, elevated provider quota/errors, backup verification failure, suspected cross-owner access, token/data exposure, or sandbox isolation failure. Contain first (disable provider/sandbox or restrict API), preserve safe operational evidence, rotate affected credentials, assess learner-data scope, recover from verified backups, and document the owner-approved notification decision. Assign actual on-call and notification destinations before production; none are provisioned here.

## Clean install and rollback

From a clean checkout, install locked backend/frontend dependencies, run migrations and all offline checks, build the wheel and containers, then deploy only to an explicitly approved disposable environment. For rollback, stop new worker claims, retain the database, deploy the previous immutable image digest, then resume workers and verify readiness. Do not run destructive database restore without an explicit disposable target and verified backup.

## Backups and disaster recovery

Use `ops/backup.sh` and `ops/restore.sh` only with a disposable PostgreSQL URL in verification. Production backup cadence, RPO/RTO, storage, encryption, and restore authority remain unselected until the hosting architecture is approved.
