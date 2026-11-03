# Security policy

Supported versions: latest `main` until a stable release is published.

Do **not** publish a vulnerability with exploit details in a public issue. Use
GitHub's private vulnerability reporting when enabled on this repository, or
contact the repository maintainer through their publicly listed GitHub profile.
No guarantee of a specific response SLA is made.

Trust boundaries: uploaded GTFS files are untrusted text. Run the CLI with normal
user permissions, never as root. The reader does not fetch URLs or execute feed
contents, but it currently loads entire CSV tables into memory. Extremely large
or malicious ZIPs can exhaust resources; only process feeds from sources you trust.
