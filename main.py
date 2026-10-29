import argparse
import sys
from pathlib import Path

from app.config import load_config
from app.orchestrator import MultiAgentOrchestrator
from app.memory_store import MemoryStore
from app.memory_health import MemoryHealthService
from app.evaluations import run_system_evaluations, run_memory_on_off_experiment

def main():
    parser = argparse.ArgumentParser(
        description="Gemini Free-Tier + Obsidian Multi-Agent System CLI (Target 7-Agent System)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run a multi-agent task")
    run_parser.add_argument("task", type=str, help="The task description")
    run_parser.add_argument("--project", type=str, default="default", help="Project ID / scope")
    run_parser.add_argument("--no-revise", action="store_true", help="Disable reviewer revisions to save quota")
    run_parser.add_argument("--mock", action="store_true", help="Run in mock/offline mode without calling live Gemini API")

    # Command: feedback
    fb_parser = subparsers.add_parser("feedback", help="Provide human feedback on a completed run")
    fb_parser.add_argument("run_id", type=str, help="Run ID")
    fb_parser.add_argument("text", type=str, help="Feedback description")

    # Command: approve
    app_parser = subparsers.add_parser("approve", help="Approve pending lessons from a run into Approved memory")
    app_parser.add_argument("run_id", type=str, help="Run ID")

    # Command: reject
    rej_parser = subparsers.add_parser("reject", help="Reject pending lessons from a run")
    rej_parser.add_argument("run_id", type=str, help="Run ID")
    rej_parser.add_argument("reason", type=str, nargs="?", default="User rejected", help="Rejection rationale")

    # Command: archive
    arch_parser = subparsers.add_parser("archive", help="Archive an approved lesson")
    arch_parser.add_argument("lesson_id", type=str, help="Lesson ID or filename (without .md)")
    arch_parser.add_argument("--reason", type=str, default="User archived", help="Reason for archival")

    # Command: restore
    rest_parser = subparsers.add_parser("restore", help="Restore an archived lesson back to approved")
    rest_parser.add_argument("lesson_id", type=str, help="Lesson ID or filename (without .md)")

    # Command: health-check
    hc_parser = subparsers.add_parser("health-check", help="Conduct a read-only audit of the Obsidian vault")
    hc_parser.add_argument("--scope", type=str, default=None, help="Filter scope by project ID")
    hc_parser.add_argument("--fix", type=str, default=None, help="Finding ID to apply approved fix for (e.g. FIND-001)")
    hc_parser.add_argument("--restore-backup", type=str, default=None, help="Backup folder ID to restore")

    # Command: evaluate
    eval_parser = subparsers.add_parser("evaluate", help="Run local deterministic benchmark suite or Memory ON/OFF experiment")
    eval_parser.add_argument("--on-off", action="store_true", help="Run comparative Memory ON vs OFF experiment")

    # Command: list-runs
    subparsers.add_parser("list-runs", help="List all run folders in Obsidian vault")

    # Command: status
    subparsers.add_parser("status", help="Check configuration and system status")

    args = parser.parse_args()
    config = load_config()
    store = MemoryStore(config.vault_path)

    if args.command == "status":
        print(f"=== Gemini + Obsidian Multi-Agent System ===")
        print(f"Project Root: {config.project_root}")
        print(f"Vault Path:   {config.vault_path} (Exists: {config.vault_path.exists()})")
        print(f"Model:        {config.gemini_model}")
        print(f"API Key:      {'Configured' if config.gemini_api_key else 'Missing or Placeholder'}")
        print(f"Max Calls:    {config.max_api_calls_per_run}")
        print(f"Live Tools:   {config.allow_live_tools}")
        return

    if args.command == "list-runs":
        runs = store.list_runs()
        if not runs:
            print("No runs recorded yet in Obsidian-Brain/03_Runs/")
        else:
            print(f"Found {len(runs)} runs:")
            for r in runs:
                print(f" - {r}")
        return

    if args.command == "feedback":
        fb_path = store.save_feedback(args.run_id, args.text)
        print(f"[OK] Feedback saved for run {args.run_id} -> {fb_path.name}")
        return

    if args.command == "approve":
        success = store.approve_run_lesson(args.run_id)
        if success:
            print(f"[OK] Lessons from run {args.run_id} approved and moved to 01_Memory/Approved/{args.run_id}.md")
        else:
            print(f"[ERROR] Pending lesson note not found for run {args.run_id} in 01_Memory/Pending/")
            sys.exit(1)
        return

    if args.command == "reject":
        success = store.reject_run_lesson(args.run_id, args.reason)
        if success:
            print(f"[OK] Lessons from run {args.run_id} moved to 01_Memory/Rejected/{args.run_id}.md (Reason: {args.reason})")
        else:
            print(f"[ERROR] Pending lesson note not found for run {args.run_id} in 01_Memory/Pending/")
            sys.exit(1)
        return

    if args.command == "archive":
        success = store.archive_lesson(args.lesson_id, reason=args.reason)
        if success:
            print(f"[OK] Lesson '{args.lesson_id}' archived to 01_Memory/Archived/ (Reason: {args.reason})")
        else:
            print(f"[ERROR] Lesson '{args.lesson_id}' not found in 01_Memory/Approved/")
            sys.exit(1)
        return

    if args.command == "restore":
        success = store.restore_lesson(args.lesson_id)
        if success:
            print(f"[OK] Lesson '{args.lesson_id}' restored from 01_Memory/Archived/ to 01_Memory/Approved/")
        else:
            print(f"[ERROR] Lesson '{args.lesson_id}' not found in 01_Memory/Archived/")
            sys.exit(1)
        return

    if args.command == "health-check":
        health_svc = MemoryHealthService(config.vault_path, config.app_data_path)
        if args.fix:
            res = health_svc.apply_approved_fix(args.fix)
            if res.get("success"):
                print(f"[OK] Fix applied: {res.get('message')} (Backup: {res.get('backup_id')})")
            else:
                print(f"[ERROR] Fix failed: {res.get('message')}")
            return

        if args.restore_backup:
            ok = health_svc.restore_backup(args.restore_backup)
            if ok:
                print(f"[OK] Successfully restored notes from backup '{args.restore_backup}'")
            else:
                print(f"[ERROR] Failed to restore backup '{args.restore_backup}'")
            return

        report = health_svc.scan(scope=args.scope)
        print(f"=== Memory Health Audit Report ===")
        print(f"Timestamp:       {report.timestamp}")
        print(f"Approved Notes:  {report.approved_notes_count} ({report.total_approved_bytes} bytes)")
        print(f"Pending Notes:   {report.pending_notes_count}")
        print(f"Conflicts:       {report.conflicts_count}")
        print(f"Archived Notes:  {report.archived_notes_count}")
        print(f"Findings:        {len(report.findings)}")
        if not report.findings:
            print("\n[OK] Vault is HEALTHY. No duplicates, contradictions, secrets, or stale notes detected.")
        else:
            print("\nIdentified Issues:")
            for f in report.findings:
                print(f"\n* [{f.risk_level}] {f.finding_id} ({f.finding_type}): {f.reason}")
                print(f"  Affected: {', '.join(f.affected_note_ids)}")
                print(f"  Suggested Action: {f.suggested_action}")
                if f.proposed_diff:
                    print(f"  Proposed Diff/Fix:\n    " + f.proposed_diff.replace("\n", "\n    "))
        return

    if args.command == "evaluate":
        if args.on_off:
            print("[*] Running Memory ON vs Memory OFF Experiment...")
            exp = run_memory_on_off_experiment(config)
            print(f"\n=== Memory ON vs OFF Experiment Results ===")
            print(f"Tasks Evaluated: {exp.tasks_count}")
            print(f"Memory ON Pass Rate:  {exp.memory_on_pass_rate_pct}%")
            print(f"Memory OFF Pass Rate: {exp.memory_off_pass_rate_pct}%")
            print(f"Delta Improvement:    +{exp.difference_pct}%")
            print(f"Summary: {exp.summary}")
            for tr in exp.task_results:
                print(f"\nTask: {tr.task}")
                print(f" - Memory ON:  Success={tr.memory_on_success} ({tr.memories_used_on} notes used)")
                print(f" - Memory OFF: Success={tr.memory_off_success} ({tr.memories_used_off} notes used)")
                print(f" - Observation: {tr.observation}")
        else:
            print("[*] Running Local Deterministic Benchmark Suite (10 Benchmarks)...")
            rep = run_system_evaluations(config)
            print(f"\n=== System Evaluation Report ===")
            print(f"Total Benchmarks:  {rep.total_benchmarks}")
            print(f"Passed Benchmarks: {rep.passed_benchmarks}")
            print(f"Pass Rate:         {rep.pass_rate_pct}%")
            print("\nBenchmark Breakdown:")
            for r in rep.results:
                status_tag = "[PASS]" if r.passed else "[FAIL]"
                print(f" {status_tag} {r.benchmark_id}: {r.name} -> {r.evidence}")
        return

    if args.command == "run":
        # Check if live key is available or mock requested
        mock = args.mock or not config.gemini_api_key
        if not config.gemini_api_key and not args.mock:
            print("[INFO] No live GEMINI_API_KEY detected in .env. Running in verified mock/offline mode.")
            mock = True

        orchestrator = MultiAgentOrchestrator(config, mock_mode=mock)
        print(f"[*] Starting Multi-Agent Task: {args.task}")
        print(f"[*] Mode: {'Mock/Offline' if mock else 'Live Gemini Free-Tier'}")
        
        try:
            result = orchestrator.execute_task(
                task=args.task,
                project_id=args.project,
                allow_revise=not args.no_revise
            )
            print("\n================ FINAL DELIVERY ================")
            print(f"Run ID:   {result['run_id']}")
            print(f"Status:   {result['status']}")
            print(f"Verdict:  {result['verdict']}")
            print(f"API Calls Used: {result['run_metadata']['api_calls']}")
            mem_dec = result.get("memory_decision", {})
            if result.get("saved_candidate_ids"):
                cand_paths = [f"Obsidian-Brain/01_Memory/Pending/{cid}.md" for cid in result["saved_candidate_ids"]]
                print(f"Pending lessons:     {', '.join(cand_paths)}")
            else:
                print(f"Memory assessment:   No long-term memory needed (Score {mem_dec.get('score', 0)}/10: {mem_dec.get('rationale', 'Routine')})")
            print("\nResult Excerpt:")
            print(result["result"][:400] + ("..." if len(result["result"]) > 400 else ""))
            print("================================================")
        except Exception as e:
            print(f"\n[ERROR] Task execution failed: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
