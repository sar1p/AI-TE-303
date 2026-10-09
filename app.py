"""Local warehouse route demonstration with an optional diagnostic adapter."""

import json
from uuid import uuid4

import streamlit as st

from interface.diagnostics import DiagnosticState, evaluate_diagnostics
from interface.evidence import environment_metadata
from interface.rendering import grid_html
from interface.session import SimulationSession
from search_algorithm.grid import GridError
from search_algorithm.scenarios import available_scenarios

st.set_page_config(page_title="Warehouse Route Lab | AI-TE-303", page_icon="🧭", layout="wide")
st.html("""<style>
[data-testid="stMainBlockContainer"] {padding:2.25rem 1.5rem 3rem;}
@media (max-width:1100px) {
  .st-key-mission_layout [data-testid="stHorizontalBlock"] {flex-direction:column;}
  .st-key-mission_layout [data-testid="stColumn"] {width:100%; flex:1 1 100%;}
}
</style>""")


def reset_session(scenario):
    st.session_state.simulation = SimulationSession(scenario)


def apply_action(event, movement_allowed):
    try:
        st.session_state.simulation.apply_event(event, movement_allowed=movement_allowed)
    except GridError as error:
        st.error(str(error))
    else:
        st.rerun()


choices = available_scenarios()
if not choices:
    st.error("No search scenarios are available. Check data/search_scenarios.")
    st.stop()
by_id = {scenario.id: scenario for _, scenario in choices}
with st.sidebar:
    st.caption("AI-TE-303 · SIMULATION")
    st.title("Warehouse Route Lab")
    selected = st.selectbox("Scenario", list(by_id),
                            format_func=lambda key: by_id[key].title, key="scenario_choice")
    scenario = by_id[selected]
    st.caption(scenario.description)
    if "simulation" not in st.session_state or st.session_state.simulation.scenario.id != selected:
        reset_session(scenario)
    if st.button("Reset simulation", key="reset_simulation", width="stretch"):
        reset_session(scenario)
        st.rerun()
    use_gate = st.toggle("Apply diagnostic safety gate", value=False, key="diagnostic_gate")
    st.caption("Search-only mode is independent of diagnosis. Enable the gate to require a valid diagnosis before movement.")
    st.divider()
    st.markdown("**Two modules, one simulation**")
    st.caption("Search: D* Lite + A* baseline\n\nDiagnostics: teammate-owned expert system")
    st.caption("Reloading the browser creates a new session. Reset restarts the selected scenario.")

session = st.session_state.simulation
st.caption("DYNAMIC NAVIGATION / WAREHOUSE SIMULATION")
st.title("Dynamic route planning")
st.write("Explore a fixed-goal robot mission and compare incremental D* Lite with a fresh A* search.")
if "simulation_error" in st.session_state:
    st.error(st.session_state.pop("simulation_error"))
route_tab, diagnosis_tab, evidence_tab = st.tabs(["Route planner", "Diagnostics", "Evidence & methods"])

with diagnosis_tab:
    st.subheader("Robot observations")
    st.caption("Use the observation names defined by the teammate's expert system. Missing or null facts mean unknown.")
    raw_text = st.text_area("Raw observations (JSON)", value="{}", height=170, key="raw_facts")
    try:
        facts = json.loads(raw_text)
    except ValueError as error:
        diagnostic = DiagnosticState("error", f"Invalid observations JSON: {error}")
        facts = None
    else:
        diagnostic = evaluate_diagnostics(facts)
    if diagnostic.status == "pending":
        st.info("Expert system pending — the teammate will implement rules, inference, explanations, and diagnostic tests.")
        st.markdown("See **docs/TEAMMATE_TASKS.md** and **docs/MODULE_CONTRACTS.md**. This application does not generate a diagnosis while that module is absent.")
    elif diagnostic.status == "error":
        st.error(diagnostic.message)
    else:
        result = diagnostic.result
        st.write(f"Diagnosis status: **{result['status']}**")
        if diagnostic.can_move:
            st.success("The diagnostic safety gate allows movement.")
        else:
            st.warning("The diagnostic safety gate pauses movement. Review the evidence and recommendations.")
        st.markdown("**Suspected conditions**")
        st.dataframe(result["findings"], hide_index=True, width="stretch")
        st.markdown("**Recommendations**")
        st.dataframe(result["recommendations"], hide_index=True, width="stretch")
        st.markdown("**Rule explanations**")
        st.json(result["rule_trace"])
        st.write("Missing facts:", result["missing_facts"])

movement_allowed = not use_gate or diagnostic.can_move

with route_tab:
    if not use_gate:
        status_label = "Expert system pending" if diagnostic.status == "pending" else "Diagnosis evaluated separately"
        st.info(f"Search-only demonstration · {status_label}")
    if use_gate and not movement_allowed:
        st.warning("Diagnostic safety gate active: robot movement is paused. Map edits and route planning remain available.")
    metrics = st.columns(4)
    metrics[0].metric("Route status", session.dstar_result.status.title())
    metrics[1].metric("Remaining moves", session.dstar_result.cost if session.dstar_result.cost is not None else "—")
    metrics[2].metric("Map revision", session.planner.grid.revision)
    metrics[3].metric("Robot position", f"{session.planner.start[0]}, {session.planner.start[1]}")

    map_panel, control_panel = st.container(key="mission_layout").columns([2.1, 1], gap="large")
    with map_panel:
        with st.container(border=True):
            st.subheader(scenario.title)
            overlay = st.radio("Route overlay", ["D* Lite", "A*"], horizontal=True, key="route_overlay")
            shown = session.dstar_result if overlay == "D* Lite" else session.astar_result
            st.html(grid_html(session.planner.grid, shown.path, session.planner.start, session.planner.goal))
            st.caption("Coordinates: row, column · 4 neighbors · unit movement cost · fixed goal")
            if shown.status == "unreachable":
                st.warning("No route is available. Reopen a passage or reset the scenario.")
    with control_panel:
        st.subheader("Mission controls")
        next_event = next((event for event in scenario.events if event["id"] not in session.applied_events), None)
        if next_event:
            st.caption(f"Next scenario event: {next_event.get('label', next_event['id'])}")
        else:
            st.caption("All scripted events completed. Continue exploring the map or reset.")
        next_paused = next_event and next_event["type"] == "move" and not movement_allowed
        if st.button("Apply next scenario event", type="primary", width="stretch", key="next_event",
                     disabled=next_event is None or bool(next_paused)):
            apply_action(next_event, movement_allowed)
        remaining = [event for event in scenario.events if event["id"] not in session.applied_events]
        run_paused = not movement_allowed and any(event["type"] == "move" for event in remaining)
        if st.button("Run remaining scenario", width="stretch", key="run_remaining",
                     disabled=not remaining or run_paused):
            try:
                for event in remaining:
                    session.apply_event(event, movement_allowed=movement_allowed)
            except GridError as error:
                st.session_state.simulation_error = f"Scenario stopped: {error} Reset before replaying after manual edits."
                st.rerun()
            else:
                st.rerun()
        if st.button("Move robot one step", width="stretch", key="move_robot",
                     disabled=not movement_allowed or len(session.dstar_result.path) < 2):
            apply_action({"id": f"manual-move-{uuid4()}", "type": "move", "label": "Manual robot step"}, movement_allowed)

        st.divider()
        st.markdown("**Edit a map cell**")
        with st.form(f"edit_cell_{scenario.id}"):
            row = st.number_input("Row", min_value=0, max_value=session.planner.grid.height - 1, step=1)
            column = st.number_input("Column", min_value=0, max_value=session.planner.grid.width - 1, step=1)
            action = st.selectbox("Cell state", ["Blocked", "Open"])
            edit = st.form_submit_button("Apply cell change", width="stretch")
        if edit:
            apply_action({"id": f"manual-map-{uuid4()}", "type": "map", "label": "Manual map edit",
                          "changes": [{"cell": [row, column], "blocked": action == "Blocked"}]}, movement_allowed)

    st.subheader("Actual planning work")
    comparison = []
    for name, attribute in [("D* Lite", "dstar_lite"), ("A*", "astar")]:
        current = session.records[-1][attribute]["metrics"]
        comparison.append({
            "Algorithm": name, "States processed (last call)": current["processed_states"],
            "Queue pops": current["queue_pops"], "Queue pushes": current["queue_pushes"],
            "Planning time (ms)": round(current["elapsed_ms"], 3),
            "States processed (session)": sum(record[attribute]["metrics"]["processed_states"] for record in session.records),
        })
    st.dataframe(comparison, hide_index=True, width="stretch")
    st.caption("Times measure planning and route extraction, excluding UI rendering and map edits. Use the benchmark tool for complete update-and-plan timings. The algorithms count different state-processing operations.")
    with st.expander("Incremental state and event history"):
        st.write({"initializations": session.planner.initialization_count, "key_offset_k_m": session.planner.k_m,
                  "retained_g_entries": len(session.planner.g), "retained_rhs_entries": len(session.planner.rhs)})
        st.dataframe([{key: record[key] for key in ("event_id", "label", "map_revision", "start", "k_m")}
                      for record in session.records], hide_index=True, width="stretch")

with evidence_tab:
    st.subheader("Reproduce the running results")
    st.write("Export the current input map, applied events, computed routes, metrics, and source metadata.")
    payload = {"metadata": environment_metadata(), **session.to_dict(),
               "diagnostics": {"adapter_status": diagnostic.status, "result": diagnostic.result,
                               "safety_gate_enabled": use_gate, "raw_observations_json": raw_text}}
    st.download_button("Download session evidence (JSON)", json.dumps(payload, indent=2, allow_nan=False),
                       file_name=f"{scenario.id}-session.json", mime="application/json", key="download_evidence")
    st.code("python -m pytest -q\npython -m search_algorithm.main\npython tools/replay_demo.py --output artifacts/demo\npython tools/benchmark_search.py --output artifacts/benchmark --repeats 5", language="bash")
    st.markdown("**D* Lite** fits a moving start, a fixed goal, and changing connectivity. It retains prior search values and repairs affected vertices. **A*** is simpler for one static query. Both are optimal for this finite unit-cost model.")
    st.markdown("D* Lite can spend more time on initialization or widespread changes. It does not predict moving obstacles, coordinate multiple robots, or control physical hardware. The expert system needs documented rules and its own verification.")
    st.caption("Recorded timings depend on the machine, map, implementation, and event sequence. No universal performance or physical robot reliability claim is made.")
