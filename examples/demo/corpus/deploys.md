# Deploy process

Deploys roll out in three waves over 20 minutes. Roll back with `deployctl rollback checkout` if error rate exceeds 1% in any wave. Deploys are frozen during the last week of each quarter.
