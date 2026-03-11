#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
cd "$SCRIPT_DIR/.."

version="${1:-}"
if [[ -z $version ]]; then
  echo "USAGE: $0 version" >&2
  exit 1
fi

if [[ "$(git symbolic-ref --short HEAD)" != "main" ]]; then
  echo "must be on main branch" >&2
  exit 1
fi

waitForPr() {
  local pr=$1
  while true; do
    if gh pr view "$pr" | grep -q 'MERGED'; then
      break
    fi
    echo "Waiting for PR to be merged..."
    sleep 5
  done
}

# ensure we are up-to-date
uncommitted_changes=$(git diff --compact-summary)
if [[ -n $uncommitted_changes ]]; then
  echo -e "There are uncommitted changes, exiting:\n${uncommitted_changes}" >&2
  exit 1
fi
git pull origin main
unpushed_commits=$(git log --format=oneline origin/main..main)
if [[ -n $unpushed_commits ]]; then
  echo -e "\nThere are unpushed changes, exiting:\n$unpushed_commits" >&2
  exit 1
fi

# bump version in pyproject.toml
sed -i -e "s!^version = \".*\"\$!version = \"${version}\"!" pyproject.toml

# update lockfile to match
uv lock

# commit on a release branch and open a PR
git add pyproject.toml uv.lock
git branch -D "release-${version}" 2>/dev/null || true
git checkout -b "release-${version}"
git commit -m "release: bump version to ${version}"
git push origin "release-${version}"
pr_url=$(gh pr create \
  --base main \
  --head "release-${version}" \
  --title "Release ${version}" \
  --body "Release ${version} of puss-say")

# extract PR number from URL
pr_number=$(echo "$pr_url" | grep -oE '[0-9]+$')

# enable auto-merge and delete branch after merge
gh pr merge "$pr_number" --auto --merge --delete-branch
git checkout main

waitForPr "release-${version}"
git pull origin main

# create GitHub release (this also creates the tag)
gh release create "${version}" --draft --title "${version}" --notes ""
