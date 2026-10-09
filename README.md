# Azure Simple IP

Azure public service tag IP ranges as plain text, automatically refreshed daily.
Each file contains one CIDR prefix per line. Folder and file names use snake_case.

## Files

- `service_tags_public_latest.txt`: all prefixes from all service tags.
- `service_tags/<tag_name>/ips.txt`: all prefixes for a service tag.
- `service_tags/<tag_name>/ipv4.txt`: IPv4 prefixes only.
- `service_tags/<tag_name>/ipv6.txt`: IPv6 prefixes only.

Prefixes can overlap or repeat across service tags. Empty lists produce empty files.

## Updates

GitHub Actions checks Microsoft's latest public service tags daily at 03:17 UTC
and commits only changed IP files to the default branch. Removed service tags are
deleted. Runs can also be started manually from the Actions tab.

The workflow must be on the default branch, and repository rules must allow
GitHub Actions to push commits to it. Scheduled runs may be delayed; GitHub can
disable schedules in public repositories after 60 days without activity.

## Run Locally

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```sh
uv run --locked python main.py
```

Source: [Microsoft Azure public service tags](https://download.microsoft.com/download/7/1/D/71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_Latest.json).
