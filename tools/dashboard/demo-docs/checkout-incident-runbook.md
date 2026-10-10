# Checkout service incident runbook

This runbook covers the checkout service: the API that turns a cart into a paid order. It is fictional sample content for the ctxd dashboard demo.

## Scope

Use this runbook for alerts on checkout latency, checkout error rate, payment provider failures and order queue backlog. Inventory and search incidents have their own runbooks.

## Dashboards and alerts

The checkout dashboard shows request rate, error rate, p95 latency, payment provider latency and order queue depth. Alerts fire on error rate above 2% for five minutes or p95 latency above 3 seconds.

## Severity levels

SEV1: customers cannot complete any purchase. SEV2: a payment method or region is failing, or p95 latency is above 3 seconds. SEV3: degraded but working, such as slow confirmation emails.

## First five minutes

Acknowledge the page. Open the checkout dashboard and confirm the alert is real. Post in the incident channel with the alert name, start time and your role. Declare a severity before you start debugging.

## Roles

The incident commander coordinates and makes decisions. The operations lead runs commands. The communications lead updates the status page every 30 minutes for SEV1 and every hour for SEV2.

## Payment provider timeouts

When calls to the payment provider time out, check the provider status page first. If the provider is degraded, enable the fallback provider with the `checkout.payments.fallback` flag. Do not raise client timeouts above 10 seconds; long waits hold database connections.

## Database connection pool exhausted

Symptoms: requests wait for a connection and fail after the pool timeout. Check for long-running transactions and kill any older than 60 seconds. If load is the cause, scale out read replicas before raising the pool size; a larger pool can overload the primary.

## Order queue backlog

If the order queue grows faster than workers drain it, scale the order workers to the maximum replica count. Orders stay safe in the queue; customers see "order received" while fulfilment catches up.

## Elevated error rate after a deploy

If errors rise within 15 minutes of a deploy, roll back first and investigate second. Use the deploy tool's rollback command; never patch production by hand during an incident.

## Rate limiting and traffic spikes

During a flash sale or bot traffic, enable the stricter rate-limit profile for anonymous sessions. Logged-in customers keep the normal limit so that real purchases continue.

## Feature flags

Every risky checkout change ships behind a flag. During an incident, list flags changed in the last 24 hours and turn off any that touch the failing path.

## Customer communication

The status page message must say what is affected, what customers should do, and when the next update will be posted. Do not promise a fix time.

## Escalation

Escalate to the payments engineering manager if a SEV1 is not mitigated within 30 minutes, or if a payment provider must be contacted directly.

## Resolution and handover

An incident is mitigated when customers can buy again and is resolved when the root cause is fixed. Hand over open actions with an owner and a due date.

## Postmortem

Write a blameless postmortem within five working days for every SEV1 and SEV2. Include the timeline, impact, root cause, what went well, and follow-up actions.
