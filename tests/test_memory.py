"""Exercise data preservation and concurrency behavior in isolated stores."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / ".kiro/skills/dream/scripts/memory.py"
spec = importlib.util.spec_from_file_location("memory", SCRIPT)
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        memory.ROOT = Path(self.tmp.name) / ".kiro/memory"
        self.root = memory.ROOT
        initial = self.root / "stores/initial"
        initial.mkdir(parents=True)
        (initial / "MEMORY.md").write_text("# Memory Index\n")
        (initial / "processed.json").write_text("{}\n")
        (self.root / "episodes").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_quiet(self, fn, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            fn(*args)
        return json.loads(out.getvalue())

    def candidate(self):
        data = self.run_quiet(memory.begin, 20)
        path = self.root / "dreams" / data["dream"]
        names = list(memory.read_json(path / "manifest.json")["episodes"])
        (path / "report.md").write_text(
            "# Report\nReviewed: " + ", ".join(names) + "\n"
            "No unsupported preferences promoted. Existing evidence retained.\n"
            "## Verification\nNo tooling preference is established. No deployment is verified. "
            "The empty index correctly returns no known decisions.\n")
        return data["dream"], path

    def test_empty_checkout_status_and_validation_are_read_only(self):
        before = memory.inventory(self.root)
        self.assertEqual(self.run_quiet(memory.status)["version"], "initial")
        memory.validate(memory.active()[1])
        self.assertEqual(before, memory.inventory(self.root))

    def test_promotion_preserves_inputs_and_late_episodes_then_rollback(self):
        (self.root / "episodes/one.md").write_text("Explicit correction")
        before = memory.inventory(self.root / "stores/initial")
        name, path = self.candidate()
        snapshot = memory.inventory(path / "input")
        (self.root / "episodes/two.md").write_text("Arrived after dream started")
        self.run_quiet(memory.promote, name)
        self.assertEqual(memory.active()[0], name)
        self.assertEqual([p.name for p in memory.pending(memory.active()[1])], ["two.md"])
        self.assertEqual(before, memory.inventory(self.root / "stores/initial"))
        self.assertEqual(snapshot, memory.inventory(path / "input"))
        self.run_quiet(memory.rollback, "initial")
        self.assertEqual(len(memory.pending(memory.active()[1])), 2)
        self.assertTrue((self.root / "stores" / name).exists())

    def test_concurrent_candidate_cannot_overwrite_new_active_version(self):
        first, _ = self.candidate()
        second, _ = self.candidate()
        self.run_quiet(memory.promote, first)
        with self.assertRaisesRegex(ValueError, "Active memory changed"):
            memory.promote(second)
        self.assertEqual(memory.active()[0], first)

    def test_changed_source_blocks_promotion(self):
        episode = self.root / "episodes/one.md"
        episode.write_text("Original")
        name, _ = self.candidate()
        episode.write_text("Changed")
        with self.assertRaisesRegex(ValueError, "Source episode changed"):
            memory.promote(name)
        self.assertEqual(memory.active()[0], "initial")

    def test_broken_index_and_symlink_rejected(self):
        name, path = self.candidate()
        (path / "output/MEMORY.md").write_text("# Memory\n- [Missing](topics/missing.md)\n")
        with self.assertRaisesRegex(ValueError, "broken"):
            memory.promote(name)
        (path / "output/MEMORY.md").write_text("# Memory\n")
        (path / "output/escape").symlink_to(self.root / "episodes")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            memory.promote(name)

    def test_a_processed_episode_cannot_be_silently_rewritten(self):
        episode = self.root / "episodes/one.md"
        episode.write_text("Original")
        name, _ = self.candidate()
        self.run_quiet(memory.promote, name)
        episode.write_text("New meaning")
        with self.assertRaisesRegex(ValueError, "Processed episode changed"):
            memory.pending(memory.active()[1])

    def test_writer_lock_and_path_traversal_rejected(self):
        with memory.lock():
            with self.assertRaisesRegex(ValueError, "writer lock"):
                memory.begin(20)
        self.assertFalse((self.root / ".write-lock").exists())
        with self.assertRaises(ValueError):
            memory.rollback("../outside")

    def test_topic_with_evidence_can_be_promoted(self):
        name, path = self.candidate()
        topics = path / "output/topics"
        topics.mkdir()
        (topics / "testing.md").write_text(
            "---\nname: testing\ndescription: Test workflow\ntype: project\nupdated: 2026-09-06\n---\n"
            "## Test runner\nKind: fact\nScope: repository\nEvidence: pyproject.toml inspected today\n"
            "Use the repository test runner.\n")
        (path / "output/MEMORY.md").write_text("# Memory Index\n- [Testing](topics/testing.md) — Test workflow.\n")
        self.run_quiet(memory.promote, name)
        self.assertEqual(memory.validate(memory.active()[1])["topics"], 1)

    def test_unreviewed_episode_and_modified_snapshot_rejected(self):
        (self.root / "episodes/one.md").write_text("Original")
        name, path = self.candidate()
        report = path / "report.md"
        report.write_text(report.read_text().replace("one.md", "omitted"))
        with self.assertRaisesRegex(ValueError, "account for episode"):
            memory.promote(name)
        (path / "input/MEMORY.md").write_text("# Modified input\n")
        with self.assertRaisesRegex(ValueError, "input snapshot changed"):
            memory.promote(name)


if __name__ == "__main__":
    unittest.main()
