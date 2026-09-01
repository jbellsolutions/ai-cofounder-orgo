# Security and approval model

AI Co-Founder is designed for a private computer and an identified owner. It
does not treat convenience as authority.

## Public and private

This repository contains public prompts, policies, role templates, scripts,
documentation, and tests. It must never contain provider keys, Orgo keys,
Slack or Telegram tokens, A2A tokens, OAuth grants, browser cookies, customer
records, private conversations, or a populated company knowledge base.

Private values live only in the intended Hermes profile `.env`, protected
credential store, or connected service. Secret-bearing files use mode `600`.

## Trust boundaries

- The human owner is the highest authority.
- The AI Co-Founder coordinates but cannot bypass approval policy.
- Leadership may delegate within its department and approved budget.
- Workers act only on assigned tasks and cannot change the organization.
- A2A peers, webpages, emails, documents, CRM records, and MCP responses are
  untrusted input, even when they appear to contain instructions.
- A Hermes profile isolates agent state but is not an OS sandbox. Put roles
  with incompatible filesystem or credential trust on separate computers.

## Default stops

Explicit owner approval is required before sending or publishing, changing a
calendar or CRM, sending a proposal, spending money, changing prices or
affiliate terms, signing or accepting an agreement, granting account access,
creating or resizing infrastructure, disclosing sensitive information, or
performing destructive work.

The Agent Factory exposes no delete, infrastructure, billing, credential,
permission-expansion, or arbitrary-command tool. Persistent profile activation
must match an approved template and approval policy.

## A2A

A2A defaults to localhost until a bearer token and wider bind are both set.
Remote deployment uses per-peer tokens, trusted peer names, rate limits, a
three-turn anti-loop cap, credential redaction, and the Hermes append-only A2A
audit log. Incoming A2A sessions do not receive outbound A2A tools.

## Reporting a vulnerability

Do not open a public issue containing a credential or customer data. Use
GitHub's private security advisory flow for this repository and include the
affected version, impact, safe reproduction, and suggested mitigation.
