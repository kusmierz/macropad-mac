# Security Review

Reviewed: 2026-08-11  
Scope: Python application and daemon, local web UI/API, HID programming, macOS permissions and persistence, build process, dependencies, configuration, tests, and research utilities.

## Verdict

**Recommendation: REQUEST CHANGES. The menu-bar application and local HTTP server are not safe to run as-is.**

The most serious issue is an unauthenticated loopback API that can pass attacker-controlled actions to an intentional `shell=True` execution feature. The UI also contains a stored cross-site scripting path that can invoke the same privileged API.

The checkout changed during the review and was observed at times with unresolved rebase conflicts. A checkout containing conflict markers is not runnable independently of the security findings. The vulnerabilities below were present in the clean `main` and `4x4` code inspected during the review.

## Findings

### Critical: unauthenticated local API permits command execution

Evidence:

- `app.py:128-171` accepts state-changing POST requests without a session token, authentication, or `Origin`, `Host`, and `Referer` validation.
- `app.py:155-160` passes `/api/test` input directly to the action dispatcher.
- `actions.py:88-89` executes `shell:` actions with `subprocess.Popen(arg, shell=True)`.
- `app.py:175-176` and `menubar.py:96-103` expose the API on fixed loopback port `8777`.

Impact:

- Any process or other logged-in user able to connect to the loopback port can execute commands as the user running Makropad.
- A hostile website may also reach the endpoint when browser Local Network Access policy permits it or the user grants access. The handler does not enforce `application/json`, while `text/plain` is a CORS-safelisted content type.
- The same API can overwrite profiles, start input capture, and reprogram the connected HID device.

Required remediation:

1. Generate a high-entropy per-launch secret and require it in a custom header on every API request.
2. Validate the exact expected `Host` and `Origin`; reject missing or unexpected values.
3. Require `Content-Type: application/json`, impose a small request-size limit, and add read timeouts.
4. Prevent `/api/test` from executing `shell:` actions. Prefer removing shell actions or making them explicitly opt-in.
5. Fail closed if port `8777` is already occupied.

References:

- [WHATWG Fetch: CORS-safelisted request headers](https://fetch.spec.whatwg.org/#cors-safelisted-request-header)
- [Chrome Local Network Access](https://developer.chrome.com/blog/local-network-access)
- [Python subprocess security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations)

### High: stored DOM XSS in profile rendering

Evidence:

- `ui.html:343-352` returns raw profile-controlled app, URL, and shell values from `pretty()`.
- `ui.html:540-549` inserts those values into `innerHTML` when rendering knob actions.

A crafted profile value can execute JavaScript in the trusted local UI origin. That script can call the command execution, profile, capture, and HID programming endpoints.

Required remediation:

- Construct the row elements separately and assign all profile-derived values using `textContent`.
- Add a restrictive Content Security Policy and `X-Content-Type-Options: nosniff` as defense in depth.

### Medium: executable profile storage is not hardened

Evidence:

- `paths.py:19-24` stores source-mode profiles inside the repository and frozen profiles under Application Support.
- `store.py` writes the profile directly with ordinary `open(..., "w")` semantics.
- The inspected `profiles.yaml` was mode `0644` and contained one shell action.

Profiles are executable configuration because they can launch applications, open URLs, synthesize input, and run shell commands. Direct writes are non-atomic, follow symlinks, and inherit the process umask.

Required remediation:

- Create profile data with mode `0600`.
- Verify ownership and avoid following symlinks.
- Write to a same-directory temporary file, flush it, and replace the destination atomically.
- Do not place credentials or secrets directly in shell actions.

### Medium: mutable dependency and build chain

Evidence:

- `requirements.txt` specifies lower bounds rather than reviewed versions.
- `build.sh:16-17` upgrades pip and installs the latest available PyInstaller and rumps packages.

Building the application therefore downloads and executes mutable third-party code without a reproducible dependency set.

Required remediation:

- Maintain reviewed runtime and build constraints or a lock file.
- Pin compatible versions and hashes for release builds.
- Build releases in an isolated environment and record the dependency manifest.

### Medium: stale persistence artifact and shared log path

Evidence:

- `launchd/no.macropad.daemon.plist:11-16` hardcodes another user's project path.
- The LaunchAgent uses `KeepAlive` and logs to `/tmp/macropad-daemon.log`.

Required remediation:

- Generate the LaunchAgent using the actual installed application path.
- Store logs under `~/Library/Logs/Makropad.log` with restrictive permissions.
- Document and test complete removal of LaunchAgents and macOS privacy permissions.

### Low: research scripts modify the device immediately

`research/map_test.py`, `research/media_test.py`, and `research/media_test2.py` open the HID vendor interface and overwrite bindings immediately when executed.

Require an explicit `--yes` flag or interactive confirmation before any write. These scripts should not be included as normal user-facing commands.

## Positive observations

The reviewed code contained no telemetry, outbound application service, hardcoded credential, `sudo` use, Python `eval`/`exec`, or unsafe YAML loader. The HTTP server binds to loopback rather than a LAN interface, and ordinary subprocess calls generally use argument arrays. These properties reduce risk but do not mitigate the unauthenticated command endpoint.

## Validation

- Approximately 40 source, configuration, build, test, documentation, and research artifacts were inspected.
- A clean snapshot of the 16-key branch completed 18 unit tests successfully.
- A checkout observed later during the review contained unresolved conflict markers and failed at import; it must not be run until the rebase is fully resolved.
- No HTTP listener was started, no dependency was installed, no macOS privacy permission was requested, and no HID write was performed during the review.

## Safer interim usage

Until the critical and high findings are fixed, avoid running `app.py`, `menubar.py`, or the privileged daemon. On a clean checkout, the lower-risk path is CLI-only validation followed by deliberate flashing for the exact supported device model. Flashing still overwrites device bindings; do not run the research utilities against a device whose configuration matters.
