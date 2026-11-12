"""The Fable-directed workflow (2026-11-11): the roles are wired (CLAUDE.md, the fable-director skill, the agents, the
project's model), the cost meter prices a session log correctly, the section reader finds sections, and the reference
breakdown measures a clip whose cuts, punch-in, push and beat are known."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit"))
sys.path.insert(0, str(ROOT / "kit/refs"))
sys.path.insert(0, str(ROOT / "kit/look"))

import cost  # noqa: E402
import doc  # noqa: E402

ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")

AGENTS = {"edit-critic": "opus", "reference-analyst": "opus", "fact-scout": "sonnet",
          "edit-builder": "sonnet", "qa-reader": "haiku"}


def frontmatter(path):
    text = path.read_text()
    assert text.startswith("---\n"), path
    head = text[4:text.index("\n---\n", 4)]
    return dict(line.split(":", 1) for line in head.splitlines() if ":" in line and not line.startswith(" "))


# ---------------------------------------------------------------- the wiring

def test_every_agent_has_its_model_and_is_named_by_the_director():
    skill = (ROOT / ".claude/skills/fable-director/SKILL.md").read_text()
    found = {p.stem for p in (ROOT / ".claude/agents").glob("*.md")}
    assert found == set(AGENTS)
    for name, model in AGENTS.items():
        fm = frontmatter(ROOT / f".claude/agents/{name}.md")
        assert fm["name"].strip() == name
        assert fm["model"].strip() == model, f"{name} runs on {fm['model']}"
        assert fm["description"].strip()
        assert f"`{name}`" in skill, f"the director's skill never mentions {name}"


def test_only_the_director_runs_on_fable_and_judging_never_drops_below_opus():
    # the owner, 2026-11-12: Fable 5.2 directs, every helper runs on another model. Judging a render and studying a
    # reference are taste, so they stay on Opus (2026-11-11: "no compromise on the edit's quality"); the mechanical
    # helpers are the ones on Sonnet and Haiku.
    assert AGENTS["edit-critic"] == AGENTS["reference-analyst"] == "opus"
    assert "fable" not in " ".join(AGENTS.values())
    skill = (ROOT / ".claude/skills/fable-director/SKILL.md").read_text()
    assert "## Handing down is the default" in skill and "kit/cost.py --limit=1 --crew" in skill
    for name in ("edit-builder", "qa-reader"):
        tools = frontmatter(ROOT / f".claude/agents/{name}.md")["tools"]
        assert "WebSearch" not in tools and "Agent" not in tools
    assert "Edit" not in frontmatter(ROOT / ".claude/agents/qa-reader.md")["tools"]
    assert "Edit" not in frontmatter(ROOT / ".claude/agents/edit-critic.md")["tools"]


def test_the_project_starts_on_fable_and_points_at_the_director():
    settings = json.loads((ROOT / ".claude/settings.json").read_text())
    assert settings["model"] == "claude-fable-5-2"
    assert settings["modelSettings"]["claude-fable-5-2"]["effortLevel"] == "high"
    assert settings["env"]["HYPERFRAMES_NO_UPDATE_CHECK"] == "1"          # the pin the renders rely on survives
    assert "fable-director" in (ROOT / "CLAUDE.md").read_text()
    assert frontmatter(ROOT / ".claude/skills/fable-director/SKILL.md")["name"].strip() == "fable-director"
    for skill in ("video-shorts", "canvas-studio"):
        assert "edit-critic" in (ROOT / f".claude/skills/{skill}/SKILL.md").read_text()
    assert "edit-critic" in (ROOT / "kit/qa/CRITIC.md").read_text()


def test_files_the_director_skill_names_exist():
    skill = (ROOT / ".claude/skills/fable-director/SKILL.md").read_text()
    for rel in ("kit/cost.py", "kit/doc.py", "kit/qa/stills.py", "kit/qa/digest.py", "kit/refs/breakdown.py", "kit/refs/compare.py",
                "kit/qa/CRITIC.md", "kit/refs/OWNER_DEFAULTS.md", "kit/hf/README.md", "kit/refs/EDITING.md"):
        assert rel in skill and (ROOT / rel).exists(), rel


# ---------------------------------------------------------------- the cost meter

def log_line(mid, model, **usage):
    return json.dumps({"type": "assistant", "timestamp": "2026-11-11T10:00:00Z", "message": {"id": mid, "model": model, "usage": usage}})


def test_cost_counts_a_message_once_and_prices_it(tmp_path):
    usage = dict(input_tokens=1000, output_tokens=1000, cache_read_input_tokens=1_000_000, cache_creation_input_tokens=1_000_000,
                 cache_creation={"ephemeral_1h_input_tokens": 1_000_000, "ephemeral_5m_input_tokens": 0},
                 output_tokens_details={"thinking_tokens": 400})
    log = tmp_path / "abc.jsonl"
    log.write_text("\n".join([
        log_line("m1", "claude-fable-5-2", **usage), log_line("m1", "claude-fable-5-2", **usage),      # one message, two blocks
        log_line("m2", "claude-sonnet-5-5", input_tokens=0, output_tokens=100_000),
        json.dumps({"type": "custom-title", "customTitle": "A test edit"}), "not json"]))
    sub = tmp_path / "abc" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-x.jsonl").write_text(log_line("s1", "claude-haiku-5-5", input_tokens=200_000, output_tokens=0))
    (sub / "agent-x.meta.json").write_text(json.dumps({"agentType": "qa-reader", "description": "read the reports"}))
    s = cost.session(log)
    fable = s["main"]["claude-fable-5-2"]
    assert s["title"] == "A test edit" and fable["messages"] == 1 and fable["thinking"] == 400
    # $8 in, $40 out, $16 one-hour cache write, $0.20 cache read, per million
    assert fable["usd"] == pytest.approx(0.008 + 0.04 + 16 + 0.20)
    assert fable["usd_read"] == pytest.approx(0.20) and fable["usd_write"] == pytest.approx(16)
    assert s["main"]["claude-sonnet-5-5"]["usd"] == pytest.approx(1.0)
    agent = s["subagents"][0]
    assert agent["agent"] == "qa-reader"
    assert agent["models"]["claude-haiku-5-5"]["usd"] == pytest.approx(200_000 * 0.10 * 5 / 1e6)   # over 100K: x5


def tool_line(tid, name, **inp):
    return json.dumps({"type": "assistant", "message": {"id": "m" + tid, "model": "claude-fable-5-2", "usage": {"output_tokens": 1},
                                                        "content": [{"type": "tool_use", "id": tid, "name": name, "input": inp}]}})


def test_crew_names_who_ran_who_never_did_and_the_checks_the_director_ran_itself(tmp_path):
    agents = tmp_path / "agents"
    agents.mkdir()
    for name in ("edit-builder", "edit-critic", "qa-reader"):
        (agents / f"{name}.md").write_text("---\n---\n")
    log = tmp_path / "abc.jsonl"
    log.write_text("\n".join([
        tool_line("t1", "Agent", subagent_type="edit-critic", description="round 1"),
        tool_line("t2", "Agent", subagent_type="edit-critic", description="round 2"),
        tool_line("t2", "Agent", subagent_type="edit-critic", description="round 2"),                   # the same call, logged twice
        tool_line("t3", "Bash", command="python3 kit/qa/digest.py -- node kit/qa/precheck.mjs hf/index.html"),
        tool_line("t4", "Bash", command="python3 kit/hf/plan_check.py films/x/visual_plan.json && uv run python -m kit.film films/x joins"),
        tool_line("t5", "Bash", command="ls films/x"),
        tool_line("t6", "Read", file_path="kit/qa/qa.py"), "not json"]))
    c = cost.crew(log, agents)
    assert c["started"] == {"edit-critic": 2} and c["never"] == ["edit-builder", "qa-reader"]
    assert c["checks"] == {"precheck": 1, "plan_check": 1, "joins": 1}
    first, second = cost.crew_lines(c, turns=7)
    assert first == "  crew: edit-critic 2. Never started: edit-builder, qa-reader."
    assert second.startswith("  the main session ran 3 checks itself (") and "in 7 turns" in second
    assert second.endswith("qa-reader and edit-builder never ran.")
    quiet = cost.crew_lines({"started": {"qa-reader": 1}, "never": [], "checks": {}}, turns=3)
    assert quiet == ["  crew: qa-reader 1."]


def test_cost_reports_an_unknown_model_without_a_price(tmp_path):
    log = tmp_path / "x.jsonl"
    log.write_text(log_line("m1", "some-other-model", input_tokens=10, output_tokens=10))
    row = cost.session(log)["main"]["some-other-model"]
    assert row["priced"] is False and row["usd"] == 0


# ---------------------------------------------------------------- the section reader

MD = """# Manual
intro
## 1. Cutting
cut text
```
# not a heading
```
### Joins
join text
## The lens: the camera on him
lens text
## 12. Podcasts
pod text
"""


def test_doc_sections_and_matching():
    lines, secs = doc.sections(MD)
    titles = [s[1] for s in secs]
    assert titles == ["Manual", "1. Cutting", "Joins", "The lens: the camera on him", "12. Podcasts"]
    cutting = next(s for s in secs if s[1] == "1. Cutting")
    body = "\n".join(lines[cutting[2]:cutting[3]])
    assert "join text" in body and "# not a heading" in body and "lens text" not in body    # sub-sections included
    assert doc.matches("The lens: the camera on him", "the LENS")
    assert doc.matches("1. Cutting", "1") and not doc.matches("12. Podcasts", "1")


def test_doc_prints_one_section(tmp_path):
    f = tmp_path / "m.md"
    f.write_text(MD)
    out = subprocess.run([sys.executable, str(ROOT / "kit/doc.py"), str(f), "lens"], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == "## The lens: the camera on him\nlens text"
    miss = subprocess.run([sys.executable, str(ROOT / "kit/doc.py"), str(f), "nothing here"], capture_output=True, text=True)
    assert miss.returncode != 0 and "no section matches" in miss.stderr


# ---------------------------------------------------------------- the check digest

CHECK = """checking plan
ERROR   recruiter+ch03: away from him 28.7 s (never more than 12 s): split the takeover with a face beat
WARN    intern: 'chat' has only been used in paper_studio, not noir: check it renders in this look
WARN    elon: 'chat' has only been used in paper_studio, not noir: check it renders in this look
WARN    rewind: a takeover of 0.9 s (4-12 s): too short
WARN    later: a takeover of 2.4 s (4-12 s): too short
WARN    shift: compare on screen 10.2 s, over its 10 s maximum
FAIL: visual_plan.json  41 passages, 1 errors, 5 warnings
"""


def test_digest_keeps_errors_groups_repeats_and_ends_on_the_verdict():
    sys.path.insert(0, str(ROOT / "kit/qa"))
    import digest
    out = digest.digest(CHECK)
    assert out[0].startswith("ERROR   recruiter+ch03: away from him 28.7 s")              # word for word
    assert "WARN x2  'chat' has only been used in paper_studio, not noir: check it renders in this look  [intern, elon]" in out
    assert any(l.startswith("WARN x2  a takeover of 0.9 s") and "[rewind, later]" in l for l in out)   # numbers may differ
    assert "WARN    shift: compare on screen 10.2 s, over its 10 s maximum" in out      # a single warning stays whole
    assert out[-1] == "FAIL: visual_plan.json  41 passages, 1 errors, 5 warnings" and len(out) == 5


def test_digest_passes_the_exit_code_on():
    run = subprocess.run([sys.executable, str(ROOT / "kit/qa/digest.py"), "--", sys.executable, "-c",
                          "import sys; print('WARN    a: x'); print('verdict'); sys.exit(3)"], capture_output=True, text=True)
    assert run.returncode == 3 and run.stdout.strip().splitlines() == ["WARN    a: x", "verdict"]


# ---------------------------------------------------------------- the reference breakdown

def picture(seed, w=640, h=360):
    """A busy picture with corners to track: blocks and circles on grey."""
    import cv2
    rng = np.random.default_rng(seed)
    im = np.full((h, w, 3), 90, np.uint8)
    for _ in range(70):
        x, y = int(rng.integers(0, w - 40)), int(rng.integers(0, h - 40))
        colour = tuple(int(c) for c in rng.integers(30, 255, 3))
        if rng.random() < 0.5:
            cv2.rectangle(im, (x, y), (x + int(rng.integers(12, 60)), y + int(rng.integers(12, 60))), colour, -1)
        else:
            cv2.circle(im, (x + 20, y + 20), int(rng.integers(6, 26)), colour, -1)
    return im


def zoomed(im, z):
    import cv2
    h, w = im.shape[:2]
    cw, ch = w / z, h / z
    M = np.float32([[z, 0, -(w - cw) / 2 * z], [0, z, -(h - ch) / 2 * z]])
    return cv2.warpAffine(im, M, (w, h), flags=cv2.INTER_LINEAR)


@pytest.fixture(scope="module")
def reference(tmp_path_factory):
    """6 s at 30 fps: picture A (2 s), A punched in x1.25 (2 s), picture B pushed x1.00 -> x1.15 (2 s); a click every
    0.5 s (120 BPM), so both cuts sit on the beat."""
    d = tmp_path_factory.mktemp("ref")
    a, b = picture(1), picture(2)
    frames = [a] * 60 + [zoomed(a, 1.25)] * 60 + [zoomed(b, 1 + 0.15 * k / 59) for k in range(60)]
    src = d / "ref.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "640x360", "-r", "30", "-i", "-",
                          "-f", "lavfi", "-t", "6", "-i", "aevalsrc='0.6*sin(2*PI*880*t)*exp(-40*mod(t\\,0.5))':s=44100",
                          "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src)], stdin=subprocess.PIPE)
    p.communicate(b"".join(f.tobytes() for f in frames))
    assert p.returncode == 0
    out = d / "out"
    run = subprocess.run([sys.executable, str(ROOT / "kit/refs/breakdown.py"), str(src), f"--out={out}", "--no-ocr"],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-800:]
    return out, json.loads((out / "breakdown.json").read_text())


@ffmpeg
@pytest.mark.slow
def test_breakdown_finds_the_cuts_and_names_them(reference):
    _, B = reference
    assert B["cuts"] == pytest.approx([2.0, 4.0], abs=0.04)
    first, second = B["cut_events"]
    assert first["kind"] == "punch-in" and first["scale"] == pytest.approx(1.25, abs=0.04)
    assert second["kind"] == "new picture"


@ffmpeg
@pytest.mark.slow
def test_breakdown_measures_the_push(reference):
    _, B = reference
    assert [len(s["moves"]) for s in B["shots"]] == [0, 0, 1]             # nothing moves in the two still shots
    push = B["shots"][2]["moves"][0]
    assert push["kind"] == "push" and push["zoom"] == pytest.approx(1.15, abs=0.03)
    assert push["seconds"] == pytest.approx(2.0, abs=0.25) and push["easing"] == "linear"
    assert abs(push["pan"]) < 0.02                                        # a zoom about the centre is not a pan


@ffmpeg
@pytest.mark.slow
def test_breakdown_hears_the_beat_and_places_cuts_on_it(reference):
    _, B = reference
    snd = B["sound"]
    assert snd["beat"] == "clear" and snd["bpm"] == pytest.approx(120, abs=3)
    assert np.diff(snd["onsets"][:8]) == pytest.approx(0.5, abs=0.03)
    assert min(abs(o - 2.0) for o in snd["onsets"]) < 0.03                # onset times are true to the sound
    assert snd["cuts_on_beat"] == snd["cuts"] == 2


@ffmpeg
@pytest.mark.slow
def test_breakdown_writes_the_sheets_and_the_summary(reference):
    out, _ = reference
    for name in ("BREAKDOWN.md", "shots.jpg", "cuts.jpg", "moves.jpg"):
        assert (out / name).stat().st_size > 0, name
    md = (out / "BREAKDOWN.md").read_text()
    assert "1 punch-in" in md and "1 push" in md and "Beat: clear" in md


@ffmpeg
@pytest.mark.slow
def test_compare_marks_only_what_differs(reference):
    import compare
    _, B = reference
    assert not any(row[3] for row in compare.compare(B, B))
    faster = json.loads(json.dumps(B))
    faster["cuts"] = [1.0, 2.0, 3.0, 4.0, 5.0]
    faster["cut_events"][0]["scale"] = 1.1
    marked = {row[0] for row in compare.compare(B, faster) if row[3]}
    assert {"cuts / min", "punch-in size"} <= marked and "loudness LUFS" not in marked


@ffmpeg
@pytest.mark.slow
def test_a_graphic_that_pops_in_is_not_a_cut(tmp_path):
    import cv2
    a = picture(3)
    b = a.copy()
    cv2.rectangle(b, (180, 40), (460, 120), (255, 255, 255), -1)          # a card appears in one frame; nothing else moves
    src = tmp_path / "pop.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "640x360", "-r", "30", "-i", "-",
                          "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(src)], stdin=subprocess.PIPE)
    p.communicate(b"".join(f.tobytes() for f in [a] * 30 + [b] * 30))
    run = subprocess.run([sys.executable, str(ROOT / "kit/refs/breakdown.py"), str(src), f"--out={tmp_path / 'out'}", "--no-ocr"],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-800:]
    B = json.loads((tmp_path / "out" / "breakdown.json").read_text())
    assert B["cuts"] == [] and B["pops"] == pytest.approx([1.0], abs=0.04)
    assert B["sound"] == {"audio": False}


# ---------------------------------------------------------------- the stills sheet

def test_stills_sheet(tmp_path):
    from PIL import Image
    for k in range(5):
        Image.new("RGB", (320, 180), (40 * k, 80, 120)).save(tmp_path / f"t{k:02d}.png")
    run = subprocess.run([sys.executable, str(ROOT / "kit/qa/stills.py"), str(tmp_path), "--cols=3", "--width=160"],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    w, h = Image.open(tmp_path / "sheet.jpg").size
    assert w == 3 * 166 + 6 and h == 2 * (90 + 20 + 6) + 6
    again = subprocess.run([sys.executable, str(ROOT / "kit/qa/stills.py"), str(tmp_path)], capture_output=True, text=True)
    assert "5 stills" in again.stdout                                     # its own sheet is not tiled into the next one
