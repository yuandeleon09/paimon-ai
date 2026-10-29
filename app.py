import streamlit as st
from datetime import datetime
import uuid
from pathlib import Path

from app.config import load_config
from app.orchestrator import MultiAgentOrchestrator
from app.memory_store import MemoryStore
from app.runs import RunStore
from app.evaluations import run_system_evaluations, run_memory_on_off_experiment
from app.memory_health import MemoryHealthService

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Gemini Obsidian Learning Agents (V3)",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

config = load_config()
memory_store = MemoryStore(config.vault_path)
run_store = RunStore(config.app_data_path / "state.sqlite")
health_service = MemoryHealthService(config.vault_path, config.app_data_path)

# Initialize Session State
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
    run_store.create_conversation(st.session_state.conversation_id, "New Task Session")

if "project_id" not in st.session_state:
    st.session_state.project_id = "default"

if "collaborative_mode" not in st.session_state:
    st.session_state.collaborative_mode = False

if "last_health_report" not in st.session_state:
    st.session_state.last_health_report = None

# Sidebar Configuration
with st.sidebar:
    st.title("🧠 Gemini + Obsidian AI")
    st.caption("V3 Memory Health + Measurable Improvement")

    if st.button("➕ New Conversation", use_container_width=True):
        st.session_state.conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
        run_store.create_conversation(st.session_state.conversation_id, "New Task Session")
        st.rerun()

    st.divider()

    # Project Selection
    st.subheader("📁 Project Scope")
    st.session_state.project_id = st.text_input("Active Project ID", value=st.session_state.project_id)

    # Mode Toggles
    st.subheader("⚙️ Execution Mode")
    st.session_state.collaborative_mode = st.toggle(
        "🤝 Team Collaboration (Team Room)",
        value=st.session_state.collaborative_mode,
        help="Enables independent idea generation across specialists, relationship mapping, and Team Idea synthesis."
    )

    allow_revisions = st.checkbox("Allow Reviewer Revisions", value=True)

    st.divider()

    # System Status & Lean Vault Metrics
    st.subheader("📊 System & Vault Status")
    storage_rep = memory_store.get_storage_report()
    st.markdown(f"- **Model**: `{config.gemini_model}` (Free-Tier)")
    st.markdown(f"- **API Key**: {'🟢 Configured' if config.gemini_api_key else '🟠 Offline / Mock'}")
    st.markdown(f"- **Approved Knowledge**: `{storage_rep['approved_notes']}` notes")
    st.markdown(f"- **Pending Approval**: `{storage_rep['pending_notes']}` notes")
    st.markdown(f"- **Active Conflicts**: `{storage_rep['conflicts']}` notes")
    st.markdown(f"- **Archived Notes**: `{storage_rep['archived_notes']}` notes")
    st.markdown(f"- **Total Vault Size**: `{storage_rep['total_vault_kb']} KB` (Lean)")

    st.divider()

    # Previous Conversations
    st.subheader("📜 Recent Sessions")
    convs = run_store.list_conversations(st.session_state.project_id)
    for c in convs[:8]:
        label = f"{c['title']} ({c['id'][:8]})"
        if st.button(label, key=f"conv_{c['id']}", use_container_width=True):
            st.session_state.conversation_id = c["id"]
            st.rerun()

# Tabs for Main Content
main_tab, memory_tab, health_tab, team_tab, eval_tab = st.tabs([
    "💬 Chat & Task Workspace",
    "📚 Memory Center",
    "🩺 Memory Health",
    "🤝 Team Room",
    "📈 Improvement & Evaluations"
])

# ----------------- TAB 1: Chat & Task Workspace -----------------
with main_tab:
    st.header("Multi-Agent Collaborative Assistant")

    if not config.gemini_api_key:
        st.warning("⚠️ No Gemini API key detected in `.env`. System is operating in offline simulation mode.")

    # Display Conversation Messages
    messages = run_store.get_messages(st.session_state.conversation_id)
    for msg in messages:
        with st.chat_message(msg["role"]):
            if msg.get("agent_name"):
                st.caption(f"Role: {msg['agent_name']}")
            st.markdown(msg["content"])

    # Chat Input
    user_prompt = st.chat_input("Enter your request or task (e.g., 'Design an idempotent payment reservation flow')...")
    if user_prompt:
        run_store.add_message(st.session_state.conversation_id, "user", user_prompt)
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            status_container = st.status("Agents coordinating...", expanded=True)
            
            with status_container:
                st.write("🔍 Memory Manager: Retrieving approved project guidelines...")
                st.write("📋 Planner: Structuring steps and acceptance criteria...")
                if st.session_state.collaborative_mode:
                    st.write("🤝 Team Room: Gathering independent ideas and correlating relationships...")
                st.write("💻 Developer: Generating deliverable solution...")
                st.write("🧪 Tester: Formulating QA verification...")
                st.write("🧐 Reviewer: Evaluating criteria and safety boundaries...")
                st.write("🧠 Learner: Assessing value for selective memory...")

            orchestrator = MultiAgentOrchestrator(config, mock_mode=(not config.gemini_api_key))
            result = orchestrator.execute_task(
                task=user_prompt,
                project_id=st.session_state.project_id,
                allow_revise=allow_revisions,
                collaborative=st.session_state.collaborative_mode,
                conversation_id=st.session_state.conversation_id
            )

            status_container.update(label=f"Completed ({result['verdict']})", state="complete", expanded=False)

            st.markdown(result["result"])

            if result.get("team_idea"):
                with st.expander("🤝 Shared Team Idea & Contributor Attribution", expanded=False):
                    ti = result["team_idea"]
                    st.subheader(ti["title"])
                    st.markdown(ti["synthesis"])
                    if ti.get("conflicts_detected"):
                        st.error(f"Active Contradictions Flagged: {', '.join(ti['conflicts_detected'])}")
                    if ti.get("tradeoffs"):
                        st.markdown("**Tradeoffs:**\n" + "\n".join([f"- {t}" for t in ti["tradeoffs"]]))

            mem_dec = result.get("memory_decision", {})
            with st.expander("🧠 Selective Memory Assessment (V3 Smart Memory)", expanded=False):
                st.markdown(f"- **Score**: `{mem_dec.get('score', 0)}/10` (Minimum threshold: `{config.memory_min_score}`)")
                st.markdown(f"- **Stored to Obsidian**: `{mem_dec.get('should_store', False)}`")
                st.markdown(f"- **Rationale**: {mem_dec.get('rationale', 'N/A')}")
                if result.get("saved_candidate_ids"):
                    st.info(f"Candidate lesson proposals awaiting approval: `{', '.join(result['saved_candidate_ids'])}`")

            run_store.add_message(
                st.session_state.conversation_id,
                "assistant",
                result["result"],
                agent_name="orchestrator"
            )

# ----------------- TAB 2: Memory Center -----------------
with memory_tab:
    st.header("Obsidian Smart Memory Center")
    st.caption("Human-in-the-Loop review: Only high-value approved lessons become trusted memory.")

    mem_col1, mem_col2 = st.columns([1, 1])

    with mem_col1:
        st.subheader("⏳ Pending Candidate Lessons (Needs Approval)")
        pending_notes = list(memory_store.pending_dir.glob("*.md"))
        if not pending_notes:
            st.info("No pending lessons awaiting review.")
        else:
            for p_file in pending_notes:
                p_text = p_file.read_text(encoding="utf-8")
                lesson_id = p_file.stem
                with st.container(border=True):
                    st.markdown(f"**Lesson ID**: `{lesson_id}`")
                    st.text_area("Note Content", value=p_text, height=180, key=f"edit_{lesson_id}")
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        if st.button("✅ Approve Lesson", key=f"app_{lesson_id}"):
                            memory_store.approve_candidate(lesson_id)
                            st.success(f"Lesson `{lesson_id}` approved into trusted memory!")
                            st.rerun()
                    with btn_col2:
                        if st.button("❌ Reject Lesson", key=f"rej_{lesson_id}"):
                            memory_store.reject_candidate(lesson_id, reason="Rejected via UI")
                            st.warning(f"Lesson `{lesson_id}` archived.")
                            st.rerun()

    with mem_col2:
        st.subheader("✅ Approved Trusted Memory")
        approved_notes = list(memory_store.approved_dir.glob("*.md"))
        if not approved_notes:
            st.info("No approved lessons yet in vault.")
        else:
            for a_file in approved_notes:
                with st.expander(f"📄 {a_file.name}", expanded=False):
                    st.markdown(a_file.read_text(encoding="utf-8"))
                    if st.button(f"📦 Archive Note", key=f"arch_{a_file.stem}"):
                        memory_store.archive_lesson(a_file.stem, reason="User archived from dashboard")
                        st.info(f"Note `{a_file.name}` archived.")
                        st.rerun()

        st.subheader("⚠️ Detected Knowledge Conflicts")
        conflict_notes = list(memory_store.conflicts_dir.glob("*.md"))
        if not conflict_notes:
            st.success("No active contradictions in memory.")
        else:
            for c_file in conflict_notes:
                with st.expander(f"🚨 {c_file.name}", expanded=True):
                    st.markdown(c_file.read_text(encoding="utf-8"))

        st.subheader("📦 Archived Knowledge")
        archived_notes = list(memory_store.archived_dir.glob("*.md"))
        if not archived_notes:
            st.caption("No archived notes.")
        else:
            for ar_file in archived_notes:
                with st.expander(f"📦 {ar_file.name}", expanded=False):
                    st.markdown(ar_file.read_text(encoding="utf-8"))
                    if st.button(f"♻️ Restore to Approved", key=f"rest_{ar_file.stem}"):
                        memory_store.restore_lesson(ar_file.stem)
                        st.success(f"Note `{ar_file.name}` restored to Approved memory!")
                        st.rerun()

# ----------------- TAB 3: Memory Health (V3 Feature) -----------------
with health_tab:
    st.header("🩺 Memory Health Audit & Protection")
    st.caption("Non-destructive, read-only health scanner for duplicate detection, contradiction alerts, and cleanup proposals.")

    h_col1, h_col2 = st.columns([1, 2])
    with h_col1:
        if st.button("🔍 Run Memory Health Check", type="primary", use_container_width=True):
            with st.spinner("Auditing vault memory..."):
                report = health_service.scan()
                st.session_state.last_health_report = report.model_dump()
                st.success("Audit complete!")

    if st.session_state.last_health_report:
        rep = st.session_state.last_health_report
        st.markdown("### Health Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Approved Notes", rep["approved_notes_count"])
        m2.metric("Total Memory Bytes", f"{rep['total_approved_bytes']} B")
        m3.metric("Pending Approval", rep["pending_notes_count"])
        m4.metric("Active Conflicts", rep["conflicts_count"])

        st.subheader(f"Findings & Recommendations ({len(rep['findings'])})")
        if not rep["findings"]:
            st.success("🎉 Vault is completely healthy! No duplicates, contradictions, or stale facts detected.")
        else:
            for f in rep["findings"]:
                risk_color = "red" if f["risk_level"] == "HIGH" else ("orange" if f["risk_level"] == "MEDIUM" else "blue")
                with st.container(border=True):
                    st.markdown(f"**Finding `{f['finding_id']}`**: :{risk_color}[{f['risk_level']} RISK] — `{f['finding_type'].upper()}`")
                    st.markdown(f"**Reason**: {f['reason']}")
                    st.markdown(f"**Affected Notes**: `{', '.join(f['affected_note_ids'])}`")
                    st.code(f['proposed_diff'], language="diff")

                    act_col1, act_col2 = st.columns(2)
                    with act_col1:
                        if st.button(f"Approve & Apply: {f['suggested_action'].capitalize()}", key=f"apply_{f['finding_id']}"):
                            res = health_service.apply_approved_fix(f["finding_id"])
                            if res["success"]:
                                st.success(res["message"])
                                st.rerun()
                            else:
                                st.error(res["message"])
                    with act_col2:
                        st.caption("Action creates an automatic safety rollback backup in `app_data/versioning/`.")

# ----------------- TAB 4: Team Room -----------------
with team_tab:
    st.header("🤝 Team Collaboration Room")
    st.caption("Specialists contribute independent proposals, correlate relationships, and synthesize shared recommendations.")

    recent_runs = run_store.list_runs(limit=10)
    collab_runs = [r for r in recent_runs if r.get("team_idea_json")]

    if not collab_runs:
        st.info("No collaborative team runs recorded yet. Enable 'Team Collaboration' in the sidebar and run a task to see specialist idea correlation.")
    else:
        for cr in collab_runs:
            import json
            ti_data = json.loads(cr["team_idea_json"])
            with st.container(border=True):
                st.subheader(f"Task: {cr['task']}")
                st.caption(f"Run ID: {cr['run_id']} | Status: {cr['status']}")
                st.markdown(f"**Team Title**: {ti_data['title']}")
                st.markdown(ti_data["synthesis"])

                if ti_data.get("relationships"):
                    st.markdown("#### Idea Relationships")
                    for rel in ti_data["relationships"]:
                        icon = "🔗" if rel["rel_type"] in ("supports", "complements") else ("🚨" if rel["rel_type"] == "contradicts" else "➡️")
                        st.markdown(f"- {icon} **{rel['from_role'].capitalize()}** `{rel['rel_type']}` **{rel['to_role'].capitalize()}**: {rel['reason']}")

# ----------------- TAB 5: Improvement & Evaluations (V3) -----------------
with eval_tab:
    st.header("📈 Improvement & Quality Evaluations")
    st.caption("Measurable learning verification: local deterministic benchmarks and fair Memory ON vs Memory OFF trials.")

    e_sub1, e_sub2 = st.tabs(["🧪 Local Benchmark Suite (Free)", "⚖️ Memory ON vs OFF Comparison"])

    with e_sub1:
        st.subheader("Deterministic Local Benchmarks")
        st.caption("Tests memory value filtering, canonical deduplication, conflict preservation, and scoping with zero API calls.")
        if st.button("🚀 Run Local Benchmark Suite", type="primary"):
            with st.spinner("Executing benchmarks..."):
                report = run_system_evaluations(config)
                st.success(f"Benchmarks Completed: {report.passed_benchmarks}/{report.total_benchmarks} Passed ({report.pass_rate_pct}%)")

                for bm in report.results:
                    icon = "✅" if bm.passed else "❌"
                    st.markdown(f"- {icon} **{bm.benchmark_id}: {bm.name}**")
                    st.caption(f"  Evidence: {bm.evidence}")

    with e_sub2:
        st.subheader("Fair Memory ON vs Memory OFF Trial")
        st.caption("Runs identical benchmark tasks with memory retrieval enabled versus completely disabled to measure real performance gain.")
        if st.button("⚖️ Run Memory ON vs OFF Experiment", type="primary"):
            with st.spinner("Executing side-by-side comparison..."):
                exp_rep = run_memory_on_off_experiment(config)
                st.success(exp_rep.summary)

                c1, c2, c3 = st.columns(3)
                c1.metric("Memory ON Pass Rate", f"{exp_rep.memory_on_pass_rate_pct}%")
                c2.metric("Memory OFF Pass Rate", f"{exp_rep.memory_off_pass_rate_pct}%")
                c3.metric("Measured Improvement", f"+{exp_rep.difference_pct}%", delta=f"{exp_rep.difference_pct}%")

                st.markdown("### Per-Task Comparative Evidence")
                for tr in exp_rep.task_results:
                    with st.container(border=True):
                        st.markdown(f"**Task**: {tr.task}")
                        st.markdown(f"- **Memory ON**: {'✅ PASS' if tr.memory_on_success else '❌ FAIL'} ({tr.memories_used_on} approved notes used)")
                        st.markdown(f"- **Memory OFF**: {'✅ PASS' if tr.memory_off_success else '❌ FAIL'} ({tr.memories_used_off} notes used)")
                        st.caption(f"Observation: {tr.observation}")
