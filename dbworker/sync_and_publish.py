"""
Local scheduled-task entrypoint: runs the full 3DFP sync, then commits
and pushes the result directly to main if anything actually changed.

Meant to be triggered by a local scheduler (Windows Task Scheduler,
cron, launchd, etc.) instead of GitHub Actions. GitHub-hosted runner
IPs get 429'd by 3dfilamentprofiles.com's bot protection (confirmed
via a real failed run) -- a self-hosted runner fixes that but is one
more piece of always-on infrastructure to install and keep running.
Running this locally, on the same machine/IP manual runs already work
from, sidesteps the whole problem without any of that.

Uses your existing local git identity and credentials -- the same ones
`git push` already uses when you commit by hand -- rather than setting
up a separate bot identity, since this runs under your own account.

Usage:
    python dbworker/sync_and_publish.py                # full run, commit + push
    python dbworker/sync_and_publish.py --limit 10      # smoke-test, no big pull
    python dbworker/sync_and_publish.py --no-push       # commit locally, review before pushing
"""
import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKED_FILES = ["PCDB-Database.csv", "PCDB-PTouch-Import.csv", "registry/manufacturers.csv"]


def run_sync(extra_args):
    cmd = [sys.executable, os.path.join(REPO_ROOT, "dbworker", "run_full_sync.py"), "--resume"] + extra_args
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def has_changes():
    existing = [f for f in TRACKED_FILES if os.path.exists(os.path.join(REPO_ROOT, f))]
    if not existing:
        return False, []
    git("add", *existing)
    result = git("diff", "--cached", "--quiet")
    return result.returncode != 0, existing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process the first N brands (for testing)")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between brand page requests")
    ap.add_argument("--no-push", action="store_true", help="commit locally but don't push -- review first")
    args = ap.parse_args()

    extra = ["--delay", str(args.delay)]
    if args.limit:
        extra += ["--limit", str(args.limit)]

    print("Running full sync...")
    code = run_sync(extra)
    # run_full_sync.py exits 1 both when it fully failed (nothing
    # collected at all) and when it partially failed (checkpoint saved,
    # no files written this round) -- either way there's nothing new to
    # commit, so we still check has_changes() rather than treating exit
    # 1 as fatal here. A genuinely unexpected exit code is different.
    if code not in (0, 1):
        print(f"run_full_sync.py exited unexpectedly (code {code}) -- not committing.")
        sys.exit(code)
    if code == 1:
        print("Sync did not complete cleanly this run (see output above for why) "
              "-- checking whether there's still anything worth committing.")

    changed, existing = has_changes()
    if not changed:
        print("No record changes -- nothing to commit.")
        return

    print(f"Changes detected in: {existing}")
    commit = git("commit", "-m", "Sync filament data from 3DFilamentProfiles")
    print(commit.stdout, commit.stderr)
    if commit.returncode != 0:
        print("Commit failed -- if this is about missing user.name/user.email, "
              "set them once with: git config --global user.name \"...\" "
              "and git config --global user.email \"...\"")
        sys.exit(1)

    if args.no_push:
        print("Committed locally. --no-push set, skipping push -- review with "
              "`git log -1 -p` then push manually when ready.")
        return

    push = git("push", "origin", "HEAD:main")
    print(push.stdout, push.stderr)
    if push.returncode != 0:
        print("Push failed -- check your git credentials/remote (same as a manual `git push` would need).")
        sys.exit(1)
    print("Pushed to main.")


if __name__ == "__main__":
    main()
