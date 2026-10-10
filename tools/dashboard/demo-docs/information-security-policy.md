# Information security policy

Fictional sample content for the ctxd dashboard demo.

## Purpose and scope

This policy protects customer data, employee data and company systems. It applies to all employees, contractors and interns, and to every device that connects to company systems, including personal phones used for email or chat. Breaking this policy can lead to removal of access and disciplinary action.

## Data classification

Data has four classes. Public data is approved for release, such as marketing pages. Internal data is for employees only, such as the wiki. Confidential data includes customer records, contracts and source code. Restricted data includes payment card data, passwords, encryption keys and health information. Restricted data is never copied to a laptop, pasted into chat or attached to a ticket.

## Passwords and multi-factor authentication

Use the company password manager for every work password. Passwords are at least 14 characters and are never reused across systems. Multi-factor authentication is mandatory for single sign-on, source control, the cloud console and email. Hardware security keys are required for administrators. Never share a password, and never approve a multi-factor prompt that you did not start yourself.

## Secrets in code

API keys, database passwords and tokens live in the secrets manager, never in source code, configuration files or container images. A pre-commit hook and a scanner in continuous integration block commits that contain secrets. If a secret is committed by mistake, treat it as leaked: rotate it first, then remove it from the history, then report it to the security team.

## Laptops and devices

Company laptops use full disk encryption, automatic screen lock after five minutes and the device management agent. Install operating system updates within seven days of release. Lost or stolen devices are reported to the IT help desk within one hour so that the device can be locked and wiped remotely.

## Access reviews

Access follows least privilege: each person has only the access their current role needs. Managers review their team's access every quarter and remove anything that is no longer needed. Access to production databases is time-limited and logged. When an employee leaves, all of their access is removed on their last working day.

## Reporting a security incident

Report anything suspicious at once, even if you are not sure: a phishing email, an unknown login alert, a lost badge or data sent to the wrong person. Use the security incident form or page the security on-call engineer. Do not try to investigate on your own, and do not delete evidence such as the suspicious email. The security team confirms receipt within one hour.

## Vendors and third parties

Before a team buys or connects a new software service, the security team reviews the vendor. The review checks how the vendor stores data, whether it supports single sign-on and whether it has a recent independent audit report. Vendors that handle confidential or restricted data sign a data processing agreement before any data is shared.
