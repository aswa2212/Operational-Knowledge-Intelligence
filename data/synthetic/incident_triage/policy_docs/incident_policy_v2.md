---
author: SRE Team Lead
author_role: Director of Engineering
timestamp: 2026-01-15T09:00:00
---

# Incident Triage Policy — v2.1

## Severity Classification

**SEV1 — Critical (service_down, >10k users affected)**
- Immediate escalation to on-call manager and CTO required
- Declare war room within 15 minutes
- All hands response
- Action: declare_sev1_incident, page all leads

**SEV2 — High (degraded, 1k-10k users)**
- Page on-call engineer immediately
- Begin investigation within 10 minutes
- Action: slack_notify on-call channel, open incident ticket

**SEV3 — Medium (isolated, <1k users, intermittent)**
- Assign to owning team during business hours
- Monitor for 30 minutes before escalation
- Action: github_add_label sev3, assign ticket

**SEV4 — Low (cosmetic, no user impact)**
- Log and schedule fix in next sprint
- Action: github_add_label sev4, add to backlog

## Auto-Triage Rules

- DDoS detected + affected_users > 10000 → SEV1, declare incident immediately
- auth_failure + affected_users < 100 → SEV4, monitor only
- payment_failure + affected_users > 1000 → SEV2, page on-call
- crash + system_component = api_gateway → SEV1, full escalation
- degraded + affected_users < 500 → SEV3, assign to team

## Escalation Contacts

- On-call: Slack #incidents channel
- SEV1: page CTO + VP Engineering immediately
- Business hours: team leads in #engineering-leads
