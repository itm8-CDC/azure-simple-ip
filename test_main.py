import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from main import download_url, export_service_tags, main, snake_case


class service_tag_tests(unittest.TestCase):
    def test_snake_case(self):
        for original, expected in (
            ("AzureCloud.EastUS", "azure_cloud_east_us"),
            ("AzureCloud.eastus", "azure_cloud_eastus"),
            ("SQLManagement", "sql_management"),
            ("PowerBI", "power_bi"),
            ("AzureActiveDirectory", "azure_active_directory"),
            ("../AzureCloud", "azure_cloud"),
        ):
            with self.subTest(original=original):
                self.assertEqual(snake_case(original), expected)

    def test_plain_text_exports(self):
        service_tags = [
            {
                "id": "AzureCloud.EastUS",
                "properties": {
                    "addressPrefixes": ["10.0.0.0/24", "2001:db8::/32", "10.1.0.0/16"]
                },
            },
            {"id": "EmptyTag", "properties": {"addressPrefixes": []}},
            {"id": "Ipv4Only", "properties": {"addressPrefixes": ["192.0.2.0/24"]}},
        ]
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir)
            self.assertEqual(export_service_tags(service_tags, output_dir), 3)
            tag_dir = output_dir / "service_tags" / "azure_cloud_east_us"
            self.assertEqual(
                (tag_dir / "ips.txt").read_bytes(),
                b"10.0.0.0/24\n2001:db8::/32\n10.1.0.0/16\n",
            )
            self.assertEqual((tag_dir / "ipv4.txt").read_bytes(), b"10.0.0.0/24\n10.1.0.0/16\n")
            self.assertEqual((tag_dir / "ipv6.txt").read_bytes(), b"2001:db8::/32\n")
            self.assertEqual(
                (output_dir / "service_tags_public_latest.txt").read_bytes(),
                b"10.0.0.0/24\n2001:db8::/32\n10.1.0.0/16\n192.0.2.0/24\n",
            )
            self.assertEqual((output_dir / "service_tags" / "empty_tag" / "ips.txt").read_bytes(), b"")
            self.assertEqual((output_dir / "service_tags" / "ipv4_only" / "ipv6.txt").read_bytes(), b"")
            self.assertEqual(len(list(output_dir.rglob("*.txt"))), 10)
            self.assertFalse(list(output_dir.rglob("*.json")))

    def test_invalid_prefix_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir) / "output"
            with self.assertRaises(ValueError):
                export_service_tags(
                    [{"id": "AzureCloud", "properties": {"addressPrefixes": ["not_an_ip"]}}],
                    output_dir,
                )
            self.assertFalse(output_dir.exists())

    def test_folder_collisions_do_not_write_files(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            output_dir = Path(temporary_dir) / "output"
            with self.assertRaisesRegex(ValueError, "Duplicate service tag folder"):
                export_service_tags(
                    [
                        {"id": name, "properties": {"addressPrefixes": []}}
                        for name in ("AzureCloud", "azure_cloud")
                    ],
                    output_dir,
                )
            self.assertFalse(output_dir.exists())

    def test_main_downloads_and_exports(self):
        response = Mock()
        response.json.return_value = {"values": []}
        with tempfile.TemporaryDirectory() as temporary_dir:
            with (
                patch("main.requests.get", return_value=response) as get_request,
                patch("sys.argv", ["main.py", "--output-dir", temporary_dir]),
                patch("sys.stdout"),
            ):
                self.assertEqual(main(), 0)
            get_request.assert_called_once_with(download_url, timeout=60)
            response.raise_for_status.assert_called_once_with()
            self.assertEqual((Path(temporary_dir) / "service_tags_public_latest.txt").read_bytes(), b"")

    def test_download_failure_returns_nonzero(self):
        with (
            patch("main.requests.get", side_effect=requests.Timeout("Download timed out")),
            patch("sys.argv", ["main.py"]),
            patch("sys.stderr") as stderr,
        ):
            self.assertEqual(main(), 1)
            self.assertIn("Download timed out", "".join(call.args[0] for call in stderr.write.call_args_list))


if __name__ == "__main__":
    unittest.main()