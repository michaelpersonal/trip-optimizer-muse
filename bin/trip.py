#!/usr/bin/env python3
"""Call the Trip Optimizer hosted API with the stored custom.trip-optimizer credential.

Usage:
  trip.py GET /v1/trips
  trip.py POST /v1/trips --body-file new_trip.json
  trip.py PUT /v1/trips/<id>/plan --body-json '{"plan": {...}}'
  trip.py POST /v1/proposals/<pid>/apply

A thin deterministic client: the agent composes the calls per the workflows
in SKILL.md (the agent is the LLM provider; the service only holds state).
Auth goes through the authd surrogate exchange via dynamic_credentials.py;
requests use curl (not urllib) because this VM's egress proxy needs
preemptive Proxy-Authorization, which curl handles from $https_proxy.
The surrogate is passed via a 0600-perms curl config file, never argv.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import dynamic_credential_entry, ensure_allowed_url

BASE = "https://tripoptimizer.duckdns.org"
CRED = "custom.trip-optimizer"
HOSTS = ["tripoptimizer.duckdns.org"]


def _request(method, path, body=None):
    url = BASE + path
    ensure_allowed_url(url, HOSTS)
    entry = dynamic_credential_entry(CRED)
    surrogate = str(entry["surrogate"]).strip()
    placement = entry.get("placement")
    if placement != "bearer_header":
        raise RuntimeError(f"unsupported credential placement: {placement!r}")

    cmd = ["curl", "-sS", "--max-time", "60", "-X", method, url]
    data_file = None
    if body is not None:
        data_file = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(body, data_file)
        data_file.close()
        cmd += ["-H", "Content-Type: application/json", "--data-binary", "@" + data_file.name]
    # Pass the auth header via a restricted-perms config file so the
    # surrogate never appears on the command line.
    cfg = tempfile.NamedTemporaryFile("w", suffix=".curlcfg", delete=False)
    os.chmod(cfg.name, 0o600)
    cfg.write(f'header = "Authorization: Bearer {surrogate}"\n')
    cfg.close()
    cmd += ["-K", cfg.name]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    finally:
        os.unlink(cfg.name)
        if data_file:
            os.unlink(data_file.name)
    if out.returncode != 0:
        raise RuntimeError(f"curl failed: {out.stderr.strip()}")
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON response: {out.stdout[:500]}")


def main():
    p = argparse.ArgumentParser(description="Call the Trip Optimizer hosted API")
    p.add_argument("method", help="HTTP method, e.g. GET, POST, PUT, DELETE")
    p.add_argument("path", help="API path, e.g. /v1/trips")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--body-json", help="Request body as a JSON string")
    g.add_argument("--body-file", help="File containing the JSON request body")
    args = p.parse_args()

    body = None
    if args.body_json:
        body = json.loads(args.body_json)
    elif args.body_file:
        with open(args.body_file) as f:
            body = json.load(f)

    result = _request(args.method.upper(), args.path, body)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
