"""Bitbucket MCP Server - Tech lead PR workflow for Claude."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
import client

mcp = FastMCP("bitbucket")

# Default workspace/repo from env (optional, saves typing)
import os
DEFAULT_WS = os.environ.get("BITBUCKET_WORKSPACE", "")
DEFAULT_REPO = os.environ.get("BITBUCKET_REPO", "")


def _ws(workspace: str) -> str:
    return workspace or DEFAULT_WS


def _repo(repo: str) -> str:
    return repo or DEFAULT_REPO


# ─── Auth / Info ───

@mcp.tool()
def whoami() -> str:
    """Check current Bitbucket auth. Returns the authenticated user info."""
    try:
        user = client.get_user()
        return f"Logged in as: {user.get('display_name', '')} ({user.get('username', '')})"
    except Exception as e:
        return f"Auth error: {e}"


@mcp.tool()
def list_workspaces() -> str:
    """List all Bitbucket workspaces you have access to."""
    try:
        workspaces = client.list_workspaces()
        if not workspaces:
            return "No workspaces found."
        lines = [f"Workspaces ({len(workspaces)}):"]
        for w in workspaces:
            lines.append(f"- {w.get('slug', '')} ({w.get('name', '')})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ─── Repositories ───

@mcp.tool()
def list_repos(workspace: str = "") -> str:
    """
    List repositories in a workspace.

    Args:
        workspace: Workspace slug (uses default if not provided)
    """
    ws = _ws(workspace)
    if not ws:
        return "Provide a workspace or set BITBUCKET_WORKSPACE env var."
    try:
        repos = client.list_repos(ws)
        if not repos:
            return f"No repos in {ws}."
        lines = [f"Repos in {ws} ({len(repos)}):"]
        for r in repos:
            lines.append(f"- {r.get('slug', '')} | {r.get('name', '')} | updated: {r.get('updated_on', '')[:10]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_repo(workspace: str = "", repo: str = "") -> str:
    """
    Get repository details.

    Args:
        workspace: Workspace slug (uses default if not provided)
        repo: Repository slug (uses default if not provided)
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        data = client.get_repo(ws, rp)
        return (
            f"Repo: {data.get('full_name', '')}\n"
            f"Description: {data.get('description', 'N/A')}\n"
            f"Language: {data.get('language', 'N/A')}\n"
            f"Main branch: {data.get('mainbranch', {}).get('name', 'N/A')}\n"
            f"Created: {data.get('created_on', '')[:10]}\n"
            f"Updated: {data.get('updated_on', '')[:10]}\n"
            f"Private: {data.get('is_private', False)}"
        )
    except Exception as e:
        return f"Error: {e}"


# ─── Branches ───

@mcp.tool()
def list_branches(workspace: str = "", repo: str = "") -> str:
    """
    List branches in a repository.

    Args:
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        branches = client.list_branches(ws, rp)
        if not branches:
            return "No branches found."
        lines = [f"Branches ({len(branches)}):"]
        for b in branches:
            target = b.get("target", {})
            lines.append(
                f"- {b.get('name', '')} | "
                f"{target.get('hash', '')[:8]} | "
                f"{target.get('date', '')[:10]} | "
                f"{target.get('author', {}).get('raw', '')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ─── Pull Requests ───

@mcp.tool()
def list_pull_requests(workspace: str = "", repo: str = "", state: str = "OPEN") -> str:
    """
    List pull requests. Default shows open PRs.

    Args:
        workspace: Workspace slug
        repo: Repository slug
        state: PR state - OPEN, MERGED, DECLINED, SUPERSEDED (default OPEN)
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        prs = client.list_prs(ws, rp, state)
        if not prs:
            return f"No {state} PRs in {ws}/{rp}."
        lines = [f"{state} PRs in {ws}/{rp} ({len(prs)}):"]
        for pr in prs:
            author = pr.get("author", {}).get("display_name", "?")
            lines.append(
                f"\n#{pr['id']}: {pr.get('title', '')}\n"
                f"  Author: {author} | State: {pr.get('state', '')}\n"
                f"  {pr.get('source', {}).get('branch', {}).get('name', '?')} → "
                f"{pr.get('destination', {}).get('branch', {}).get('name', '?')}\n"
                f"  Updated: {pr.get('updated_on', '')[:16]} | "
                f"Comments: {pr.get('comment_count', 0)}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_pull_request(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Get full details of a pull request.

    Args:
        pr_id: Pull request ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        pr = client.get_pr(ws, rp, pr_id)
        author = pr.get("author", {}).get("display_name", "?")
        reviewers = ", ".join(r.get("display_name", "?") for r in pr.get("reviewers", []))
        participants = []
        for p in pr.get("participants", []):
            name = p.get("user", {}).get("display_name", "?")
            role = p.get("role", "")
            approved = p.get("approved", False)
            state = p.get("state")
            status = ""
            if approved:
                status = " [APPROVED]"
            elif state == "changes_requested":
                status = " [CHANGES REQUESTED]"
            participants.append(f"{name} ({role}){status}")

        return (
            f"PR #{pr['id']}: {pr.get('title', '')}\n"
            f"State: {pr.get('state', '')}\n"
            f"Author: {author}\n"
            f"Source: {pr.get('source', {}).get('branch', {}).get('name', '?')}\n"
            f"Destination: {pr.get('destination', {}).get('branch', {}).get('name', '?')}\n"
            f"Reviewers: {reviewers or 'None'}\n"
            f"Participants: {'; '.join(participants) or 'None'}\n"
            f"Comments: {pr.get('comment_count', 0)} | Task count: {pr.get('task_count', 0)}\n"
            f"Created: {pr.get('created_on', '')[:16]}\n"
            f"Updated: {pr.get('updated_on', '')[:16]}\n"
            f"Close source branch: {pr.get('close_source_branch', False)}\n"
            f"\n--- Description ---\n{pr.get('description', 'No description.')}"
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def create_pull_request(title: str, source_branch: str, dest_branch: str = "main",
                        description: str = "", reviewers: str = "",
                        close_source: bool = True,
                        workspace: str = "", repo: str = "") -> str:
    """
    Create a new pull request.

    Args:
        title: PR title
        source_branch: Source branch name
        dest_branch: Destination branch (default "main")
        description: PR description (markdown supported)
        reviewers: Comma-separated reviewer UUIDs (optional)
        close_source: Close source branch on merge (default True)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        reviewer_list = [r.strip() for r in reviewers.split(",") if r.strip()] if reviewers else None
        result = client.create_pr(ws, rp, title, source_branch, dest_branch, description, reviewer_list, close_source)
        return f"Created PR #{result.get('id', '?')}: {result.get('title', '')}\nURL: {result.get('links', {}).get('html', {}).get('href', '')}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def update_pull_request(pr_id: int, title: str = "", description: str = "",
                        reviewers: str = "", dest_branch: str = "",
                        workspace: str = "", repo: str = "") -> str:
    """
    Update a pull request (title, description, reviewers, destination).

    Args:
        pr_id: PR ID number
        title: New title (optional)
        description: New description (optional)
        reviewers: Comma-separated reviewer UUIDs to set (optional)
        dest_branch: New destination branch (optional)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        fields = {}
        if title:
            fields["title"] = title
        if description:
            fields["description"] = description
        if reviewers:
            fields["reviewers"] = [{"uuid": r.strip()} for r in reviewers.split(",") if r.strip()]
        if dest_branch:
            fields["destination"] = {"branch": {"name": dest_branch}}
        if not fields:
            return "No fields provided to update."
        client.update_pr(ws, rp, pr_id, **fields)
        return f"Updated PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def approve_pull_request(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Approve a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.approve_pr(ws, rp, pr_id)
        return f"Approved PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def unapprove_pull_request(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Remove your approval from a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.unapprove_pr(ws, rp, pr_id)
        return f"Removed approval from PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def request_changes_on_pr(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Request changes on a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.request_changes(ws, rp, pr_id)
        return f"Requested changes on PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def remove_request_changes(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Remove your request-changes from a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.remove_request_changes(ws, rp, pr_id)
        return f"Removed request-changes from PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def merge_pull_request(pr_id: int, strategy: str = "",
                       close_source: bool = True,
                       workspace: str = "", repo: str = "") -> str:
    """
    Merge a pull request.

    Args:
        pr_id: PR ID number
        strategy: Merge strategy - merge_commit, squash, or fast_forward (optional, uses repo default)
        close_source: Close/delete source branch after merge (default True)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        result = client.merge_pr(ws, rp, pr_id, strategy, close_source)
        if isinstance(result, dict):
            return f"Merged PR #{pr_id}. State: {result.get('state', 'MERGED')}"
        return f"Merge initiated for PR #{pr_id}. {result}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def decline_pull_request(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Decline (close without merging) a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.decline_pr(ws, rp, pr_id)
        return f"Declined PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


# ─── PR Details ───

@mcp.tool()
def pr_diff(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Get the full diff of a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        diff = client.pr_diff(ws, rp, pr_id)
        if len(diff) > 50000:
            return diff[:50000] + "\n\n... [TRUNCATED - diff too large, use pr_diffstat for overview]"
        return diff or "Empty diff."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def pr_diffstat(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Get diffstat (files changed summary) for a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        stats = client.pr_diffstat(ws, rp, pr_id)
        if not stats:
            return "No file changes."
        lines = [f"Files changed ({len(stats)}):"]
        for s in stats:
            status = s.get("status", "")
            old_path = s.get("old", {})
            new_path = s.get("new", {})
            path = (new_path or old_path or {}).get("path", "?")
            added = s.get("lines_added", 0)
            removed = s.get("lines_removed", 0)
            lines.append(f"  {status:10} {path} (+{added} -{removed})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def pr_commits(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    List commits in a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        commits = client.pr_commits(ws, rp, pr_id)
        if not commits:
            return "No commits."
        lines = [f"Commits ({len(commits)}):"]
        for c in commits:
            msg = c.get("message", "").split("\n")[0]
            lines.append(f"- {c.get('hash', '')[:8]} {msg} ({c.get('author', {}).get('raw', '')})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def pr_activity(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Get activity log for a pull request (approvals, comments, updates).

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        activities = client.pr_activity(ws, rp, pr_id)
        if not activities:
            return "No activity."
        lines = [f"Activity ({len(activities)}):"]
        for a in activities:
            if "approval" in a:
                user = a["approval"].get("user", {}).get("display_name", "?")
                lines.append(f"  APPROVED by {user} ({a['approval'].get('date', '')[:16]})")
            elif "update" in a:
                user = a["update"].get("author", {}).get("display_name", "?")
                lines.append(f"  UPDATED by {user} - state: {a['update'].get('state', '')}")
            elif "comment" in a:
                user = a["comment"].get("user", {}).get("display_name", "?")
                text = a["comment"].get("content", {}).get("raw", "")[:100]
                inline = a["comment"].get("inline", {})
                if inline:
                    lines.append(f"  INLINE COMMENT by {user} on {inline.get('path', '')}:{inline.get('to', '')}: {text}")
                else:
                    lines.append(f"  COMMENT by {user}: {text}")
            elif "changes_requested" in a:
                user = a["changes_requested"].get("user", {}).get("display_name", "?")
                lines.append(f"  CHANGES REQUESTED by {user}")
            else:
                lines.append(f"  {list(a.keys())}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def pr_build_status(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    Get build/pipeline statuses for a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        statuses = client.pr_statuses(ws, rp, pr_id)
        if not statuses:
            return "No build statuses."
        lines = [f"Build statuses ({len(statuses)}):"]
        for s in statuses:
            lines.append(
                f"  {s.get('state', '?'):12} | {s.get('name', s.get('key', '?'))} | "
                f"{s.get('description', '')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ─── PR Comments ───

@mcp.tool()
def list_pr_comments(pr_id: int, workspace: str = "", repo: str = "") -> str:
    """
    List all comments on a pull request.

    Args:
        pr_id: PR ID number
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        comments = client.list_pr_comments(ws, rp, pr_id)
        if not comments:
            return "No comments."
        lines = [f"Comments ({len(comments)}):"]
        for c in comments:
            user = c.get("user", {}).get("display_name", "?")
            text = c.get("content", {}).get("raw", "")
            inline = c.get("inline")
            parent = c.get("parent")
            prefix = ""
            if inline:
                prefix = f"[{inline.get('path', '')}:{inline.get('to', '')}] "
            if parent:
                prefix = f"  ↳ reply to #{parent.get('id', '?')} | "
            lines.append(
                f"\n  #{c.get('id', '?')} | {user} | {c.get('created_on', '')[:16]}\n"
                f"  {prefix}{text}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def comment_on_pr(pr_id: int, body: str, workspace: str = "", repo: str = "") -> str:
    """
    Add a general comment to a pull request.

    Args:
        pr_id: PR ID number
        body: Comment text (markdown supported)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        result = client.create_pr_comment(ws, rp, pr_id, body)
        return f"Comment #{result.get('id', '?')} added to PR #{pr_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def inline_comment_on_pr(pr_id: int, body: str, file_path: str, line: int,
                         workspace: str = "", repo: str = "") -> str:
    """
    Add an inline code review comment on a specific file and line in a PR.

    Args:
        pr_id: PR ID number
        body: Comment text (markdown supported)
        file_path: File path relative to repo root (e.g., "src/main.py")
        line: Line number (on the new/right side of the diff)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        result = client.create_pr_comment(ws, rp, pr_id, body, file_path, line)
        return f"Inline comment #{result.get('id', '?')} added on {file_path}:{line}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def reply_to_pr_comment(pr_id: int, parent_comment_id: int, body: str,
                        workspace: str = "", repo: str = "") -> str:
    """
    Reply to an existing PR comment.

    Args:
        pr_id: PR ID number
        parent_comment_id: ID of the comment to reply to
        body: Reply text
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        result = client.create_pr_comment(ws, rp, pr_id, body, parent_id=parent_comment_id)
        return f"Reply #{result.get('id', '?')} added to comment #{parent_comment_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def edit_pr_comment(pr_id: int, comment_id: int, body: str,
                    workspace: str = "", repo: str = "") -> str:
    """
    Edit an existing PR comment.

    Args:
        pr_id: PR ID number
        comment_id: Comment ID to edit
        body: New comment text
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.update_pr_comment(ws, rp, pr_id, comment_id, body)
        return f"Updated comment #{comment_id}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def delete_pr_comment(pr_id: int, comment_id: int,
                      workspace: str = "", repo: str = "") -> str:
    """
    Delete a PR comment.

    Args:
        pr_id: PR ID number
        comment_id: Comment ID to delete
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.delete_pr_comment(ws, rp, pr_id, comment_id)
        return f"Deleted comment #{comment_id}."
    except Exception as e:
        return f"Error: {e}"


# ─── Commits ───

@mcp.tool()
def list_commits(branch: str = "", workspace: str = "", repo: str = "") -> str:
    """
    List recent commits, optionally filtered by branch.

    Args:
        branch: Branch name (optional, defaults to all)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        commits = client.list_commits(ws, rp, branch)
        if not commits:
            return "No commits found."
        lines = [f"Recent commits ({len(commits)}):"]
        for c in commits:
            msg = c.get("message", "").split("\n")[0]
            lines.append(f"- {c.get('hash', '')[:8]} | {c.get('date', '')[:16]} | {msg}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ─── Pipelines ───

@mcp.tool()
def list_pipelines(workspace: str = "", repo: str = "") -> str:
    """
    List recent pipelines (builds) for a repository.

    Args:
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        pipelines = client.list_pipelines(ws, rp)
        if not pipelines:
            return "No pipelines found."
        lines = [f"Pipelines ({len(pipelines)}):"]
        for p in pipelines:
            state = p.get("state", {})
            stage = state.get("stage", {}).get("name", state.get("name", "?"))
            result_name = state.get("result", {}).get("name", "")
            target = p.get("target", {})
            ref = target.get("ref_name", "?")
            lines.append(
                f"  {p.get('uuid', '?')} | {ref} | "
                f"{stage}{(' - ' + result_name) if result_name else ''} | "
                f"{p.get('created_on', '')[:16]}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def trigger_pipeline(branch: str, custom_pattern: str = "",
                     workspace: str = "", repo: str = "") -> str:
    """
    Trigger a pipeline run for a branch.

    Args:
        branch: Branch name to run pipeline on
        custom_pattern: Custom pipeline name (optional, for custom pipelines in bitbucket-pipelines.yml)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        result = client.trigger_pipeline(ws, rp, branch, custom_pattern)
        if isinstance(result, dict):
            return f"Pipeline triggered: {result.get('uuid', '?')} on {branch}"
        return f"Pipeline triggered on {branch}. {result}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def stop_pipeline(pipeline_uuid: str, workspace: str = "", repo: str = "") -> str:
    """
    Stop a running pipeline.

    Args:
        pipeline_uuid: Pipeline UUID (from list_pipelines)
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        client.stop_pipeline(ws, rp, pipeline_uuid)
        return f"Stopped pipeline {pipeline_uuid}."
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def pipeline_steps(pipeline_uuid: str, workspace: str = "", repo: str = "") -> str:
    """
    Get steps/stages of a pipeline run.

    Args:
        pipeline_uuid: Pipeline UUID
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        steps = client.pipeline_steps(ws, rp, pipeline_uuid)
        if not steps:
            return "No steps."
        lines = [f"Steps ({len(steps)}):"]
        for s in steps:
            state = s.get("state", {})
            stage = state.get("stage", {}).get("name", state.get("name", "?"))
            result_name = state.get("result", {}).get("name", "")
            lines.append(
                f"  {s.get('uuid', '?')[:12]} | {s.get('name', '?')} | "
                f"{stage}{(' - ' + result_name) if result_name else ''} | "
                f"Duration: {s.get('duration_in_seconds', '?')}s"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


# ─── Source browsing ───

@mcp.tool()
def browse_source(path: str = "", ref: str = "main",
                  workspace: str = "", repo: str = "") -> str:
    """
    Browse repository source files at a specific ref (branch/tag/commit).

    Args:
        path: File or directory path (empty for root)
        ref: Branch name, tag, or commit hash (default "main")
        workspace: Workspace slug
        repo: Repository slug
    """
    ws, rp = _ws(workspace), _repo(repo)
    if not ws or not rp:
        return "Provide workspace and repo."
    try:
        result = client.browse_source(ws, rp, path, ref)
        if isinstance(result, dict):
            # Directory listing
            values = result.get("values", [])
            if values:
                lines = [f"Contents of {path or '/'} at {ref}:"]
                for v in values:
                    vtype = v.get("type", "")
                    vpath = v.get("path", "")
                    size = v.get("size", "")
                    indicator = "/" if vtype == "commit_directory" else f" ({size}b)"
                    lines.append(f"  {vpath}{indicator}")
                return "\n".join(lines)
            return f"Empty directory: {path or '/'}"
        # File content
        if len(result) > 50000:
            return result[:50000] + "\n\n... [TRUNCATED]"
        return result
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run()
