# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

"Add a data persistence layer. Make PawPal+ remember pets and tasks between runs by saving them to a `data.json` file. Add `save_to_json` and `load_from_json` methods to `pawpal_system.py`. In `README.md`, explain the persistence workflow and which files were modified. Ask your AI coding assistant how to use a library like `marshmallow` or a custom dictionary conversion to handle JSON serialization." This was a single prompt, left open-ended on the serialization approach — the agent had to decide and justify that itself.

**What did the agent do?**

1. Decided against adding `marshmallow` as a dependency, since every class was already a plain `@dataclass`, and a custom `to_dict`/`from_dict` pair would be simpler with no new install.
2. Edited `pawpal_system.py`: added `to_dict()`/`from_dict()` to `TimeBlock`, `Task`, `Pet`, and `Owner` — each one recursively calling the next level down (`Owner.to_dict()` calls `Pet.to_dict()` calls `Task.to_dict()` calls `TimeBlock.to_dict()`) — converting `date`/`time`/`Enum` fields to JSON-safe strings and back. Added `Owner.save_to_json(path)` / `Owner.load_from_json(path)` on top, defaulting to `data.json`.
3. Edited `app.py`: added "💾 Save" / "📂 Load" buttons to the sidebar, wired to those methods, including an `st.rerun()` after Load so the UI reflects the newly loaded owner.
4. Edited `tests/test_pawpal.py`: added round-trip tests for `Task` (including a nested `TimeBlock` and all enum fields), `Owner` (with pets/tasks), and an actual file save-then-load using `tempfile.TemporaryDirectory()`.
5. Edited `.gitignore` to exclude `data.json` (runtime user data, not source).
6. Updated `diagrams/uml_final.mmd` with the new methods on each class.
7. Updated `README.md` with a "💾 Data Persistence" section: the workflow (save → `to_dict` → `json.dump`; load → `json.load` → `from_dict`), the reasoning for skipping `marshmallow`, and the exact list of files touched.
8. Ran `pytest` after the change to confirm all tests (including the new ones) passed before considering the task done.

**What did you have to verify or fix manually?**

The agent's work was correct on the first pass for this particular task, which was itself worth checking rather than assuming — I re-read `to_dict`/`from_dict` on `Task` specifically to confirm every field (including the newer `completed_date` and `frequency` ones that had been added earlier in the project) was actually included, since a persistence layer silently dropping a field is the kind of bug that wouldn't show up until much later. I also verified by hand that the UML and README updates matched the actual code rather than just trusting the agent's description of what it did, since in earlier steps of this project the agent's own documentation had drifted from the implementation before (see section 4a in `reflection.md` for examples of UI/backend drift this same pattern caught).

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->
