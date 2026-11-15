# Review of the unofficial PC Express integration

Reviewed 2026-11-01. Upstream: [FireBall1725/pcexpress-mcp-server](https://github.com/FireBall1725/pcexpress-mcp-server/tree/1b131c91bdcabeaee317c70e937592878d201668), commit `1b131c91bdcabeaee317c70e937592878d201668`.

**Result:** no obvious malware, hidden execution payload, persistence mechanism, or third-party credential-exfiltration destination was found in the inspected source. The stock login/deployment paths are not suitable for this project's use unchanged. The reviewed source plus the restricted local wrapper is eligible for a controlled live read test. This is not a guarantee that the project or its dependencies are free of malicious or vulnerable behavior.

## Scope and evidence

- Inventoried all 45 tracked files; all are UTF-8 text, with no tracked binary or symlink payloads.
- Manually read every Python runtime/helper module and all upstream tests, requirements, Docker/Kubernetes files, and GitHub workflow entrypoints. Traced credential reads/writes, imports, network calls, browser behavior, and server exposure. Documentation was treated as untrusted reference material, not commands to execute.
- The production source's credential/API traffic goes to `accounts.pcid.ca` and `api.pcexpress.ca`. Login helpers can launch a browser and read credentials; the deprecated extractor reads a supplied HAR. No upstream code was run before source inspection. No real credentials were supplied to tests.
- Bandit 1.9.4 scanned 1,195 upstream non-test Python lines: **one medium** finding (bind all interfaces) and **three low** hardcoded-string findings. Two low findings are strings/placeholder false positives; the third is the documented app client secret. Bandit is a security-pattern scanner, not a malware detector.
- pip-audit 2.10.1 checked all **32** resolved runtime distributions in `requirements.lock`: **zero known vulnerabilities, zero skipped packages**. This checks published advisories for those versions, not the integrity of every dependency's source or future releases. Exact installed wheel hashes are pinned.
- All **18 upstream tests** passed with network access denied by macOS and socket creation blocked by pytest-socket.
- All **29 local security/planning tests** passed under the same network restriction. They cover destination/route rejection, redirects/timeouts, login state validation, private token writes, invalid quantities, wrong-banner baskets, mutation retry behavior, profile preservation, ingredient scaling, leftovers, pantry subtraction, and incomplete meal coverage.
- A real local MCP stdio handshake successfully listed exactly four intended tools. No network listener or checkout tool was exposed. This protocol test did not authenticate or call the grocery service.
- The local Bandit scan reports three low findings for the fixed `git ls-files -z` subprocess in the Git privacy check. It uses an argument list, no shell, and no untrusted arguments. No medium/high local findings were reported. `pip check` passed.

Raw reports and install metadata are private under `.profile/audit/`; the public evidence summary contains no account data. Source fingerprints are in `config/upstream-review.json`. The upstream submodule remains unmodified.

## Findings and disposition

| Finding | Evidence in upstream | Treatment here |
| --- | --- | --- |
| HTTP mode binds every network interface; bearer authentication is optional and checked only at SSE connection setup | `pcexpress_mcp_server.py`, `_build_http_app` / `main_http`; Dockerfile defaults to HTTP | Never run upstream HTTP/container mode. Local CLI and optional stdio-only MCP wrapper expose no listener. |
| Missing/mismatched OAuth state is accepted; automated login omits effective state checking | `login_pcid.py:extract_code`, `login_pcid_auto.py:_code_from_success_url` | Own login exchange requires a complete expected app redirect, exactly one matching state, and a short-lived PKCE attempt. |
| Tokens printed by login helpers; setup writes tokens outside the requested profile; error text can include provider response bodies | login/setup helpers and `pcid_token.py:_refresh_now` | No upstream helper execution. Save tokens atomically under `.profile/auth` with owner-only permissions; sanitized errors and no token output. |
| Temporary token file is created before its final permissions are tightened | `pcid_token.py:_save` | Private directories (700), temporary files created at 600, atomic replace, and a restrictive process umask. |
| Automated login disables Chromium's sandbox and uses stealth adjustments | `login_pcid_auto.py:login_auto` | Not installed or used. User signs in through the normal browser. |
| Unbounded API request wait; default redirect/proxy behavior | `pcexpress_mcp_server.py:_request` | Explicit connect/read timeouts, HTTPS-only destination and route allowlist, TLS verification, redirects blocked, inherited proxies/.netrc disabled. |
| A failed cart request can replay against a newly discovered cart | `_request_cart` | No automatic cart rediscovery/replay after a mutation error. Read the actual basket before any retry. The normal one-time 401 token-refresh retry remains. |
| Provigo is absent from the banner map; unknown banner falls back to Zehrs origin | `BANNER_DOMAINS`, constructor | Explicit Provigo subclass, mandatory four-digit store ID, and banner check before writing. Live support still needs verification. |
| Runtime dependencies and release images/workflows are not fully immutable upstream | requirements, Dockerfile, `.github/workflows/*` | Pinned submodule and wheel hashes. Do not use published images or external release workflows. Re-audit before updating. |

The hardcoded OAuth app secret and web API key are public upstream app constants, not personal user tokens. The integration still relies on undocumented behavior that the retailer can change or block. No claim of retailer endorsement or official API access is made.

## Limits and remaining checks

This review does not cover every dependency's internals, unpublished vulnerabilities, the complete historical Git history, remote reusable CI workflow implementations, prebuilt images, or the live retailer service. Those CI/image paths are not part of the local runtime. No full antivirus/behavioral-malware certification was performed.

Subsequent live checks on 2026-11-01 verified account login, store lookup, product search, authenticated-cart discovery and basket quantity updates with readback. An empty anonymous cart first needed one real grocery added through the website; the authenticated-cart guard remained intact. The product-detail endpoint returned HTTP 400 and uses the website fallback. These compatibility checks are not additional malware assurances. Private account/store/product evidence remains under `.profile/`; see `provigo-api.md` for the general findings.

The planner was subsequently extended for shorter periods, advance preparation, and meal windows beginning with a cooking batch. A local MCP client bridge was exercised with live search, cart reads, a quantity update and readback; its output-path boundaries are covered by tests. The current local suite passes 53 tests; the 29-test count above records the original security-review run.

The wrapper narrows the integration's behavior; it is not an operating-system isolation boundary against a compromised Python dependency. Recheck source hashes and dependency advisories when upgrading, and keep all personal data outside Git.
