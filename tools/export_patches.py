#!/usr/bin/env python3
# Copyright 2026 Vesper contributors
# SPDX-License-Identifier: AGPL-3.0-only

"""Export a patch series while retaining patches that still reproduce exactly.

A normal ``git format-patch`` rewrites commit IDs, blob IDs, hunk offsets, and
patch counters after every upstream rebase. This exporter first generates the
canonical new series, then tests each existing patch against the corresponding
new commit's parent using an isolated Git index. If applying the old patch
produces exactly the same tree as the newly generated patch, its original bytes
are retained. Only patches whose effect or applicability changed are rewritten.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict, deque
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from pathlib import Path
from typing import Iterable


SUBJECT_PREFIX_PATTERN = re.compile(r"^\[PATCH(?: [0-9]+/[0-9]+)?\]\s*")
SUBJECT_HEADER_PATTERN = re.compile(
    rb"^Subject:.*(?:\n[ \t].*)*", re.MULTILINE | re.IGNORECASE
)


def git(repository: Path, *arguments: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    return completed.stdout


def git_bytes(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def patch_mail(content: bytes) -> tuple[str, str, str, bytes]:
    first_line_end = content.find(b"\n")
    if first_line_end < 0 or not content.startswith(b"From "):
        raise ValueError("Patch has no mbox envelope")
    mail = content[first_line_end + 1 :]
    header_end = mail.find(b"\n\n")
    if header_end < 0:
        raise ValueError("Patch has incomplete mail headers")

    headers = BytesParser(policy=policy.default).parsebytes(mail[: header_end + 2])
    author_header = headers.get("From")
    date = headers.get("Date")
    subject = headers.get("Subject")
    if author_header is None or date is None or subject is None:
        raise ValueError("Patch is missing From, Date, or Subject")
    author_name, author_email = parseaddr(str(author_header))
    if not author_name or not author_email:
        raise ValueError("Patch has an invalid From identity")
    author = f"{author_name} <{author_email}>"

    payload = mail[header_end + 2 :]
    parts = re.split(rb"^---$", payload, maxsplit=1, flags=re.MULTILINE)
    if len(parts) != 2:
        raise ValueError("Patch has no commit-message separator")
    message = parts[0].rstrip(b"\n")
    return author, str(date), str(subject), message


def patch_subject(content: bytes) -> str:
    _, _, subject, _ = patch_mail(content)
    return SUBJECT_PREFIX_PATTERN.sub("", subject).strip()


def patch_payload(content: bytes) -> bytes:
    first_line_end = content.find(b"\n")
    if first_line_end < 0 or not content.startswith(b"From "):
        raise ValueError("Patch has no mbox envelope")
    mail = content[first_line_end + 1 :]
    header_end = mail.find(b"\n\n")
    if header_end < 0:
        raise ValueError("Patch has incomplete mail headers")
    return mail[header_end + 2 :]


def matches_commit_provenance(content: bytes, repository: Path, commit: str) -> bool:
    raw = git_bytes(
        repository,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%aD%x00%s%x00%b%x00",
        commit,
    )
    name, email, date, subject, body, _ = raw.split(b"\x00", maxsplit=5)
    author, patch_date, _, _ = patch_mail(content)
    expected_prefix = body.rstrip(b"\n")
    if expected_prefix:
        expected_prefix += b"\n"
    expected_prefix += b"---\n"
    return (
        author == f"{name.decode()} <{email.decode()}>"
        and patch_date == date.decode()
        and patch_subject(content) == subject.decode()
        and patch_payload(content).startswith(expected_prefix)
    )


def canonicalize_envelope_and_subject(old: bytes, generated: bytes) -> bytes:
    old_line_end = old.find(b"\n")
    generated_line_end = generated.find(b"\n")
    if old_line_end < 0 or generated_line_end < 0:
        raise ValueError("Patch has no mbox envelope")
    result = generated[:generated_line_end] + old[old_line_end:]
    generated_subject = SUBJECT_HEADER_PATTERN.search(generated)
    old_subject = SUBJECT_HEADER_PATTERN.search(result)
    if generated_subject is None or old_subject is None:
        raise ValueError("Patch has no Subject header")
    return result[: old_subject.start()] + generated_subject.group() + result[old_subject.end() :]


def has_author_signoff(content: bytes) -> bool:
    author, _, _, message = patch_mail(content)
    expected = f"Signed-off-by: {author}"
    return expected in message.decode("utf-8", errors="replace").splitlines()


def commit_body(repository: Path, commit: str) -> bytes:
    return git_bytes(repository, "show", "-s", "--format=%b%x00", commit).split(
        b"\x00", maxsplit=1
    )[0]


def complete_patch_diff(content: bytes, source_body: bytes) -> bytes:
    expected_prefix = source_body.rstrip(b"\n")
    if expected_prefix:
        expected_prefix += b"\n"
    expected_prefix += b"---\n"
    payload = patch_payload(content)
    if not payload.startswith(expected_prefix):
        raise ValueError("Patch body does not match source commit")
    remainder = payload[len(expected_prefix) :]
    first_diff = re.search(rb"^diff --git ", remainder, flags=re.MULTILINE)
    if first_diff is None:
        raise ValueError("Patch has no diff")
    return remainder[first_diff.start() :]


def applied_trees(
    sandbox: Path, parent: str, patch: Path, source_body: bytes
) -> set[str]:
    try:
        diff = complete_patch_diff(patch.read_bytes(), source_body)
        if b"GIT binary patch" in diff:
            normalized = diff
        else:
            normalized = re.sub(
                rb"^index [0-9a-f]+\.\.[0-9a-f]+(?: [0-7]+)?\n",
                b"",
                diff,
                flags=re.MULTILINE,
            )
        applicable_patch = sandbox.parent / "applicable.patch"
        applicable_patch.write_bytes(normalized)
        git(sandbox, "reset", "--hard", "--quiet", parent)
        git(
            sandbox,
            "apply",
            "--cached",
            "--whitespace=nowarn",
            str(applicable_patch),
        )
        return {git(sandbox, "write-tree").strip()}
    except (ValueError, subprocess.CalledProcessError):
        return set()


def filtered_commit_tree(
    repository: Path,
    sandbox: Path,
    parent: str,
    commit: str,
    pathspecs: list[str],
) -> str:
    patch = sandbox.parent / "expected.patch"
    patch.write_bytes(
        git_bytes(
            repository,
            "diff-tree",
            "--binary",
            "--full-index",
            "--no-commit-id",
            "-p",
            parent,
            commit,
            "--",
            *pathspecs,
        )
    )
    git(sandbox, "reset", "--hard", "--quiet", parent)
    git(sandbox, "apply", "--cached", "--whitespace=nowarn", str(patch))
    return git(sandbox, "write-tree").strip()


def export_patch_series(
    repository: Path,
    output_directory: Path,
    base: str,
    excludes: Iterable[str],
    require_author_signoff: bool = False,
) -> list[Path]:
    repository = repository.resolve()
    output_directory = output_directory.resolve()
    old_by_subject: dict[str, deque[bytes]] = defaultdict(deque)
    if output_directory.exists():
        for patch in sorted(output_directory.glob("*.patch")):
            content = patch.read_bytes()
            try:
                subject = patch_subject(content)
            except ValueError:
                continue
            old_by_subject[subject].append(content)

    pathspecs = [".", *(f":(exclude){path}" for path in excludes)]
    commits = [
        commit
        for commit in git(repository, "rev-list", "--reverse", f"{base}..HEAD").splitlines()
        if git(
            repository,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            f"{commit}^",
            commit,
            "--",
            *pathspecs,
        ).strip()
    ]
    if not commits:
        output_directory.mkdir(parents=True, exist_ok=True)
        for patch in output_directory.glob("*.patch"):
            patch.unlink()
        return []

    with tempfile.TemporaryDirectory(prefix="vesper-format-patch-") as directory:
        generated_directory = Path(directory) / "generated"
        generated_directory.mkdir()
        git(
            repository,
            "format-patch",
            "--zero-commit",
            "--no-signature",
            "--no-cover-letter",
            "--output-directory",
            str(generated_directory),
            f"{base}..HEAD",
            "--",
            *pathspecs,
        )
        generated = sorted(generated_directory.glob("*.patch"))
        if len(generated) != len(commits):
            raise RuntimeError(
                f"Expected one exported patch per feature commit: "
                f"{len(commits)} commits, {len(generated)} patches"
            )

        sandbox = Path(directory) / "sandbox"
        git(repository, "worktree", "add", "--quiet", "--detach", str(sandbox), base)
        selected: list[tuple[str, bytes]] = []
        try:
            for commit, generated_patch in zip(commits, generated, strict=True):
                generated_content = generated_patch.read_bytes()
                subject = patch_subject(generated_content)
                source_body = commit_body(repository, commit)
                if require_author_signoff and not has_author_signoff(generated_content):
                    raise RuntimeError(
                        f"Generated patch lacks a surviving author sign-off: {subject}"
                    )
                parent = git(repository, "rev-parse", f"{commit}^").strip()
                expected_tree = filtered_commit_tree(
                    repository, sandbox, parent, commit, pathspecs
                )
                if expected_tree not in applied_trees(
                    sandbox, parent, generated_patch, source_body
                ):
                    raise RuntimeError(f"Generated patch does not apply to {parent}: {subject}")

                selected_content = generated_content
                candidates = old_by_subject.get(subject)
                if candidates:
                    old_content = candidates.popleft()
                    old_patch = Path(directory) / "old.patch"
                    old_patch.write_bytes(old_content)
                    if (
                        matches_commit_provenance(old_content, repository, commit)
                        and expected_tree
                        in applied_trees(sandbox, parent, old_patch, source_body)
                    ):
                        selected_content = canonicalize_envelope_and_subject(
                            old_content, generated_content
                        )

                selected.append((generated_patch.name, selected_content))
        finally:
            git(repository, "worktree", "remove", "--force", str(sandbox))

        replacement = Path(directory) / "replacement"
        replacement.mkdir()
        for filename, content in selected:
            (replacement / filename).write_bytes(content)

        output_directory.mkdir(parents=True, exist_ok=True)
        for patch in output_directory.glob("*.patch"):
            patch.unlink()
        for patch in sorted(replacement.glob("*.patch")):
            shutil.copy2(patch, output_directory / patch.name)

    return sorted(output_directory.glob("*.patch"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base", required=True)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--require-author-signoff", action="store_true")
    arguments = parser.parse_args()

    for patch in export_patch_series(
        arguments.work,
        arguments.output,
        arguments.base,
        arguments.exclude,
        require_author_signoff=arguments.require_author_signoff,
    ):
        print(patch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
