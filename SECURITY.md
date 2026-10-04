# Public repository safety

Do not commit credentials, session cookies, account IDs, Runtime or Gateway ARNs, public IP addresses, customer names, billing exports, CloudTrail events, screenshots containing console details, or production configuration files.

Use placeholders such as `<AWS_ACCOUNT_ID>`, `<RUNTIME_ARN>` and `<GATEWAY_URL>`. If a secret is committed, revoke or rotate it first, then remove it from Git history before publishing a remediation commit.
