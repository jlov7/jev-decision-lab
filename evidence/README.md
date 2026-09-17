# Verification evidence

The repository includes the final unit-test log and browser-check summary. The downloadable `Jev_Decision_Lab_Full_Package.zip` delivered with this work also contains desktop/mobile screenshots, the complete lexical project scan, earlier failing/passing test logs and the authored replay evaluation. Those larger or project-specific artifacts are retained in the package rather than copied into the Git repository. References in `docs/QA.md` to those artifact paths refer to the full package.

No real provider key, client data or raw private frontier documents are included. The project scan records filenames, hashes, line counts and literal-term matches only. No literal Jev, TypeSafe or RLCD occurrence was found in the 29 supplied files; that is not a semantic-coverage or ingestion-failure verdict.

Reproduce the runtime checks:

```bash
python3 scripts/setup_lab.py
python3 -m unittest discover -s tests -v
python3 -m jev_lab check
node --check web/app.js
```

Optional development-only browser fallback:

```bash
PYTHONPATH=. python3 scripts/browser_check.py
```

This requires Playwright and the configured Chromium binary. It intentionally uses local asset rendering bridged to the actual HTTP server because the build environment blocked normal loopback browser navigation. It does not prove normal browser-network or CSP integration. Prefer a normal browser run on the target device and record that separately.

No authenticated Jev request was executed. Synthetic fixture metrics are not product-performance measurements.
