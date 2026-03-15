"""Bitbucket Cloud REST API client."""
import os
import requests
from urllib.parse import quote

BASE = "https://api.bitbucket.org/2.0"


def _auth() -> tuple[str, str]:
    """Return (email, token) for Basic Auth.

    Uses scoped Atlassian API token with email as username.
    Create at: id.atlassian.com → Security → Create API token with scopes → select Bitbucket.
    """
    token = os.environ.get("BITBUCKET_API_TOKEN", "")
    email = os.environ.get("BITBUCKET_EMAIL", "")
    if token and email:
        return email, token

    raise RuntimeError(
        "Set BITBUCKET_EMAIL and BITBUCKET_API_TOKEN env vars. "
        "Create a scoped token at: https://id.atlassian.com/manage-profile/security/api-tokens "
        "(use 'Create API token with scopes' → select Bitbucket as app)"
    )


def _get(path: str, params: dict | None = None) -> dict | str:
    user, token = _auth()
    r = requests.get(f"{BASE}{path}", auth=(user, token), params=params, timeout=30)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "json" in ct:
        return r.json()
    return r.text


def _post(path: str, json: dict | None = None) -> dict | str:
    user, token = _auth()
    r = requests.post(f"{BASE}{path}", auth=(user, token), json=json, timeout=30)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    if "json" in ct:
        return r.json()
    return r.text


def _put(path: str, json: dict | None = None) -> dict:
    user, token = _auth()
    r = requests.put(f"{BASE}{path}", auth=(user, token), json=json, timeout=30)
    r.raise_for_status()
    return r.json()


def _delete(path: str) -> str:
    user, token = _auth()
    r = requests.delete(f"{BASE}{path}", auth=(user, token), timeout=30)
    r.raise_for_status()
    return f"OK ({r.status_code})"


def _paginate_all(path: str, params: dict | None = None, max_pages: int = 5) -> list:
    """Fetch multiple pages and return combined values."""
    user, token = _auth()
    all_values = []
    url = f"{BASE}{path}"
    p = dict(params or {})
    p.setdefault("pagelen", 50)

    for _ in range(max_pages):
        r = requests.get(url, auth=(user, token), params=p, timeout=30)
        r.raise_for_status()
        data = r.json()
        all_values.extend(data.get("values", []))
        next_url = data.get("next")
        if not next_url:
            break
        url = next_url
        p = {}  # params are baked into the next URL

    return all_values


# ─── Workspace / Repos ───

def get_user() -> dict:
    return _get("/user")


def list_workspaces() -> list:
    return _paginate_all("/workspaces")


def list_repos(workspace: str) -> list:
    return _paginate_all(f"/repositories/{quote(workspace)}")


def get_repo(workspace: str, repo: str) -> dict:
    return _get(f"/repositories/{quote(workspace)}/{quote(repo)}")


# ─── Branches ───

def list_branches(workspace: str, repo: str) -> list:
    return _paginate_all(f"/repositories/{quote(workspace)}/{quote(repo)}/refs/branches")


# ─── Pull Requests ───

def _pr_base(ws: str, repo: str) -> str:
    return f"/repositories/{quote(ws)}/{quote(repo)}/pullrequests"


def list_prs(workspace: str, repo: str, state: str = "OPEN") -> list:
    return _paginate_all(_pr_base(workspace, repo), {"state": state})


def get_pr(workspace: str, repo: str, pr_id: int) -> dict:
    return _get(f"{_pr_base(workspace, repo)}/{pr_id}")


def create_pr(workspace: str, repo: str, title: str, source_branch: str,
              dest_branch: str = "main", description: str = "",
              reviewers: list[str] | None = None, close_source: bool = True) -> dict:
    body = {
        "title": title,
        "source": {"branch": {"name": source_branch}},
        "destination": {"branch": {"name": dest_branch}},
        "close_source_branch": close_source,
    }
    if description:
        body["description"] = description
    if reviewers:
        body["reviewers"] = [{"uuid": uuid} for uuid in reviewers]
    return _post(_pr_base(workspace, repo), body)


def update_pr(workspace: str, repo: str, pr_id: int, **fields) -> dict:
    return _put(f"{_pr_base(workspace, repo)}/{pr_id}", fields)


def merge_pr(workspace: str, repo: str, pr_id: int,
             strategy: str = "", close_source: bool = True) -> dict | str:
    body = {"close_source_branch": close_source}
    if strategy:
        body["merge_strategy"] = strategy  # merge_commit, squash, fast_forward
    return _post(f"{_pr_base(workspace, repo)}/{pr_id}/merge", body)


def decline_pr(workspace: str, repo: str, pr_id: int) -> dict | str:
    return _post(f"{_pr_base(workspace, repo)}/{pr_id}/decline")


def approve_pr(workspace: str, repo: str, pr_id: int) -> dict | str:
    return _post(f"{_pr_base(workspace, repo)}/{pr_id}/approve")


def unapprove_pr(workspace: str, repo: str, pr_id: int) -> str:
    return _delete(f"{_pr_base(workspace, repo)}/{pr_id}/approve")


def request_changes(workspace: str, repo: str, pr_id: int) -> dict | str:
    return _post(f"{_pr_base(workspace, repo)}/{pr_id}/request-changes")


def remove_request_changes(workspace: str, repo: str, pr_id: int) -> str:
    return _delete(f"{_pr_base(workspace, repo)}/{pr_id}/request-changes")


# ─── PR Details ───

def pr_diff(workspace: str, repo: str, pr_id: int) -> str:
    user, token = _auth()
    r = requests.get(
        f"{BASE}{_pr_base(workspace, repo)}/{pr_id}/diff",
        auth=(user, token), timeout=30, allow_redirects=True,
    )
    r.raise_for_status()
    return r.text


def pr_diffstat(workspace: str, repo: str, pr_id: int) -> list:
    return _paginate_all(f"{_pr_base(workspace, repo)}/{pr_id}/diffstat")


def pr_commits(workspace: str, repo: str, pr_id: int) -> list:
    return _paginate_all(f"{_pr_base(workspace, repo)}/{pr_id}/commits")


def pr_activity(workspace: str, repo: str, pr_id: int) -> list:
    return _paginate_all(f"{_pr_base(workspace, repo)}/{pr_id}/activity")


def pr_statuses(workspace: str, repo: str, pr_id: int) -> list:
    return _paginate_all(f"{_pr_base(workspace, repo)}/{pr_id}/statuses")


# ─── PR Comments ───

def list_pr_comments(workspace: str, repo: str, pr_id: int) -> list:
    return _paginate_all(f"{_pr_base(workspace, repo)}/{pr_id}/comments")


def create_pr_comment(workspace: str, repo: str, pr_id: int, body: str,
                      file_path: str = "", line_to: int = 0,
                      parent_id: int = 0) -> dict:
    payload: dict = {"content": {"raw": body}}
    if file_path and line_to:
        payload["inline"] = {"path": file_path, "to": line_to}
    if parent_id:
        payload["parent"] = {"id": parent_id}
    return _post(f"{_pr_base(workspace, repo)}/{pr_id}/comments", payload)


def update_pr_comment(workspace: str, repo: str, pr_id: int,
                      comment_id: int, body: str) -> dict:
    return _put(
        f"{_pr_base(workspace, repo)}/{pr_id}/comments/{comment_id}",
        {"content": {"raw": body}},
    )


def delete_pr_comment(workspace: str, repo: str, pr_id: int, comment_id: int) -> str:
    return _delete(f"{_pr_base(workspace, repo)}/{pr_id}/comments/{comment_id}")


# ─── Commits ───

def list_commits(workspace: str, repo: str, branch: str = "") -> list:
    params = {}
    path = f"/repositories/{quote(workspace)}/{quote(repo)}/commits"
    if branch:
        path += f"/{quote(branch)}"
    return _paginate_all(path, params, max_pages=2)


def get_commit(workspace: str, repo: str, commit_hash: str) -> dict:
    return _get(f"/repositories/{quote(workspace)}/{quote(repo)}/commit/{quote(commit_hash)}")


# ─── Pipelines ───

def list_pipelines(workspace: str, repo: str) -> list:
    return _paginate_all(
        f"/repositories/{quote(workspace)}/{quote(repo)}/pipelines/",
        {"sort": "-created_on"}, max_pages=2,
    )


def get_pipeline(workspace: str, repo: str, pipeline_uuid: str) -> dict:
    return _get(f"/repositories/{quote(workspace)}/{quote(repo)}/pipelines/{quote(pipeline_uuid)}")


def trigger_pipeline(workspace: str, repo: str, branch: str,
                     custom_pattern: str = "") -> dict | str:
    target: dict = {
        "type": "pipeline_ref_target",
        "ref_type": "branch",
        "ref_name": branch,
    }
    if custom_pattern:
        target["selector"] = {"type": "custom", "pattern": custom_pattern}
    return _post(
        f"/repositories/{quote(workspace)}/{quote(repo)}/pipelines/",
        {"target": target},
    )


def stop_pipeline(workspace: str, repo: str, pipeline_uuid: str) -> dict | str:
    return _post(
        f"/repositories/{quote(workspace)}/{quote(repo)}/pipelines/{quote(pipeline_uuid)}/stopPipeline"
    )


def pipeline_steps(workspace: str, repo: str, pipeline_uuid: str) -> list:
    return _paginate_all(
        f"/repositories/{quote(workspace)}/{quote(repo)}/pipelines/{quote(pipeline_uuid)}/steps/"
    )


# ─── Source browsing ───

def browse_source(workspace: str, repo: str, path: str = "", ref: str = "main") -> dict | str:
    return _get(f"/repositories/{quote(workspace)}/{quote(repo)}/src/{quote(ref)}/{path}")
