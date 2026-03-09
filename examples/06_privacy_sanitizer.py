"""Demo 06: Privacy Sanitizer — 12 builtin patterns + custom patterns."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memorus.privacy.sanitizer import PrivacySanitizer


def main() -> None:
    sanitizer = PrivacySanitizer()

    # --- Test each builtin pattern ---
    test_cases = [
        (
            "private_key",
            "Key: -----BEGIN RSA PRIVATE KEY-----\nMIIEpA...long...key\n-----END RSA PRIVATE KEY-----",
            "<PRIVATE_KEY>",
        ),
        (
            "bearer_token",
            "Auth: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "<BEARER_TOKEN>",
        ),
        (
            "anthropic_key",
            "export ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
            "<ANTHROPIC_KEY>",
        ),
        (
            "openai_key",
            "openai_key = sk-proj-abcdefghijklmnopqrstuvwxyz1234567890",
            "<OPENAI_KEY>",
        ),
        (
            "github_token",
            "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            "<GITHUB_TOKEN>",
        ),
        (
            "aws_access_key",
            "aws_access_key_id = AKIAIOSFODNN7EXAMPLE",
            "<AWS_KEY>",
        ),
        (
            "aws_secret_key",
            "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY1",
            "<AWS_SECRET>",
        ),
        (
            "db_url_creds",
            "DATABASE_URL=postgresql://admin:s3cretP@ss@db.example.com:5432/mydb",
            "<REDACTED>",
        ),
        (
            "api_key_param",
            "api_key=sk_test_FAKE0000000000000000000000",
            "<REDACTED>",
        ),
        (
            "password_field",
            'password = MyS3cretP@ssword123!',
            "<REDACTED>",
        ),
        (
            "win_user_path",
            r"Config at C:\Users\JohnDoe\AppData\Local\myapp.cfg",
            "<USER_PATH>",
        ),
        (
            "unix_user_path",
            "Config at /home/johndoe/.config/myapp.toml",
            "<USER_PATH>",
        ),
    ]

    passed = 0
    for i, (name, input_text, expected_marker) in enumerate(test_cases, 1):
        result = sanitizer.sanitize(input_text)
        found = expected_marker in result.clean_content
        status = "OK" if found else "FAIL"
        if found:
            passed += 1
        print(f"  [{i:2d}/12] {name:20s} -> {status}")
        if not found:
            print(f"          Expected '{expected_marker}' in: {result.clean_content[:80]}")

    assert passed == len(test_cases), f"Only {passed}/{len(test_cases)} patterns matched"
    print(f"\n[1/3] All {passed} builtin patterns verified")

    # --- Custom pattern ---
    custom_sanitizer = PrivacySanitizer(custom_patterns=[
        r"INTERNAL-\d{4}-[A-Z]{3}",  # Internal ticket IDs
    ])
    result2 = custom_sanitizer.sanitize("See ticket INTERNAL-0042-BUG for details")
    assert "INTERNAL-0042-BUG" not in result2.clean_content
    print("[2/3] Custom pattern: ticket ID redacted")

    # --- Safe content passes through unchanged ---
    safe = "Use pytest for running Python tests"
    result3 = sanitizer.sanitize(safe)
    assert result3.clean_content == safe
    assert not result3.was_modified
    print("[3/3] Safe content: unchanged")

    print("\nPASS: 06_privacy_sanitizer")


if __name__ == "__main__":
    main()
