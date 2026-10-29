# Local Development Security

ZeroDock runs configured Python code with the permissions of the user who starts
the gateway. It is not a sandbox or a hardened production service.

## Trust boundaries

- Run only handler files, imports, configurations, and dependencies you trust.
- Keep the default loopback address, `127.0.0.1`, unless you have reviewed the risk
  of exposing the gateway to other machines.
- Do not assume authentication, tenant isolation, resource quotas, or cloud-provider
  security controls are supplied by the local gateway.
- Native handlers can access local files, network services, and environment variables
  permitted by the host process. Reload does not create isolation between invocations.

## Diagnostics and secrets

Development error responses and terminal tracebacks expose exception details and
paths. Access logs, debugger output, or user code can also reveal request information.
Do not send production secrets through an untrusted development endpoint or publish
unsanitized logs and environment dumps.

Reload-specific messages identify scope, targets, state changes, and failures; they
do not deliberately log handler source or request bodies. That is not a claim that
all application/framework diagnostics are redacted.

Automatic `.env` loading is a proposed feature, not current behavior. Manage local
environment variables deliberately and never rely on a proposal as a secret manager.

## Repository hygiene

The ignore policy excludes common environment files, credential files, caches,
builds, temporary environments, and generated diagnostic output. Review example
environment files before publishing them; a template can still contain a real secret.

Ignore rules do not untrack files or remove credentials from existing history.
If a credential was exposed, stop publication, rotate it, and arrange appropriate
history remediation with the repository owner. Do not rely on hiding the file locally.

## Reporting concerns

Do not post a working exploit, credential, private payload, or sensitive environment
details in a public issue. Use an appropriate private maintainer contact when one
is available. A dedicated private security-reporting channel has not been verified
as part of this documentation review.
