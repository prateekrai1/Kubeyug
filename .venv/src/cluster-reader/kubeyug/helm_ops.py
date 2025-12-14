import os
import subprocess


def _should_print(verbose: bool) -> bool:
    # Env var lets you turn on logs without changing CLI flags.
    return verbose or os.getenv("KUBEYUG_VERBOSE") == "1"


def run_cmd(
    cmd: list[str],
    *,
    dry_run: bool = False,
    capture: bool = False,
    verbose: bool = False,
):
    # Print only if user explicitly asked, or if it's a dry-run (dry-run must show intent).
    if dry_run or _should_print(verbose):
        print(">", " ".join(cmd))

    if dry_run:
        return None

    return subprocess.run(cmd, check=True, text=True, capture_output=capture)


def helm_apply_release(
    *,
    release: str,
    chart: str,
    namespace: str,
    repo_name: str,
    repo_url: str,
    dry_run: bool = False,
    verbose: bool = False,
):
    run_cmd(["helm", "repo", "add", repo_name, repo_url], dry_run=dry_run, verbose=verbose)
    run_cmd(["helm", "repo", "update"], dry_run=dry_run, verbose=verbose)

    run_cmd(
        [
            "helm",
            "upgrade",
            "--install",
            release,
            chart,
            "-n",
            namespace,
            "--create-namespace",
        ],
        dry_run=dry_run,
        verbose=verbose,
    )


def helm_status(*, release: str, namespace: str, dry_run: bool = False, verbose: bool = False) -> str | None:
    res = run_cmd(
        ["helm", "status", release, "-n", namespace, "-o", "json"],
        dry_run=dry_run,
        capture=True,
        verbose=verbose,
    )
    return None if res is None else res.stdout


def helm_list(*, namespace: str | None = None, dry_run: bool = False, verbose: bool = False) -> str | None:
    cmd = ["helm", "list", "-o", "json"]
    cmd += ["-n", namespace] if namespace else ["-A"]

    res = run_cmd(cmd, dry_run=dry_run, capture=True, verbose=verbose)
    return None if res is None else res.stdout
