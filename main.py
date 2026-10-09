import argparse
import ipaddress
import re
import sys
from pathlib import Path

import requests


download_url = (
    "https://download.microsoft.com/download/7/1/D/"
    "71D86715-5596-4529-9B13-DA13A5DE5B63/ServiceTags_Public_Latest.json"
)


def snake_case(value: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if not value:
        raise ValueError("A service tag has an empty folder name")
    return value


def write_prefixes(path: Path, prefixes: list[str]) -> None:
    text = "".join(f"{prefix}\n" for prefix in prefixes)
    path.write_text(text, encoding="utf-8", newline="\n")


def export_service_tags(service_tags: list[dict], output_dir: Path) -> int:
    prepared_tags = []
    folder_names = set()
    for service_tag in service_tags:
        folder_name = snake_case(service_tag["id"])
        if folder_name in folder_names:
            raise ValueError(f"Duplicate service tag folder: {folder_name}")
        folder_names.add(folder_name)
        prefixes = service_tag["properties"]["addressPrefixes"]
        ipv4_prefixes = []
        ipv6_prefixes = []
        for prefix in prefixes:
            network = ipaddress.ip_network(prefix, strict=False)
            if network.version == 4:
                ipv4_prefixes.append(prefix)
            else:
                ipv6_prefixes.append(prefix)
        prepared_tags.append((folder_name, prefixes, ipv4_prefixes, ipv6_prefixes))

    all_prefixes = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for folder_name, prefixes, ipv4_prefixes, ipv6_prefixes in prepared_tags:
        service_tag_dir = output_dir / "service_tags" / folder_name
        service_tag_dir.mkdir(parents=True, exist_ok=True)
        write_prefixes(service_tag_dir / "ips.txt", prefixes)
        write_prefixes(service_tag_dir / "ipv4.txt", ipv4_prefixes)
        write_prefixes(service_tag_dir / "ipv6.txt", ipv6_prefixes)
        all_prefixes.extend(prefixes)
    write_prefixes(output_dir / "service_tags_public_latest.txt", all_prefixes)
    return len(prepared_tags)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download Azure public service tags as newline-delimited IP prefixes."
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("."), help="Output directory (default: current directory)"
    )
    parser.add_argument(
        "--source-url", default=download_url, help="Service tag JSON download URL"
    )
    args = parser.parse_args()
    try:
        response = requests.get(args.source_url, timeout=60)
        response.raise_for_status()
        service_tags = response.json()["values"]
        count = export_service_tags(service_tags, args.output_dir)
    except (requests.RequestException, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Exported {count} service tags to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
