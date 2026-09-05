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

    def topic(self, claim="Use the repository test runner.", updated="2026-09-06"):
        return ("---\nname: testing\ndescription: Test workflow\ntype: project\n"
                f"updated: {updated}\n---\n"
                "## Test runner\nKind: fact\nScope: repository\n"
                f"Evidence: pyproject.toml inspected today\n{claim}\n")

    def store_with_topic(self):
        """Promote one topic so later dreams have an existing claim to protect."""
        (self.root / "episodes/one.md").write_text("First claim")
        name, path = self.candidate()
        (path / "output/topics").mkdir()
        (path / "output/topics/testing.md").write_text(self.topic())
        (path / "output/MEMORY.md").write_text(
            "# Memory Index\n- [Testing](topics/testing.md) — Test workflow.\n")
        self.run_quiet(memory.promote, name, True)
        self.store = name
        return name

    def test_unattended_promotion_accepts_additions(self):
        self.store_with_topic()
        (self.root / "episodes/two.md").write_text("Second claim")
        name, path = self.candidate()
        topics = path / "output/topics"
        (topics / "testing.md").write_text(self.topic(updated="2026-09-07") + (
            "\n## Coverage\nKind: fact\nScope: repository\nEvidence: episode two\n"
            "Coverage runs in CI.\n"))
        (topics / "deploy.md").write_text(
            "---\nname: deploy\ndescription: Deploys\ntype: project\nupdated: 2026-09-07\n---\n"
            "## Target\nKind: decision\nScope: repository\nEvidence: episode two\nStaging first.\n")
        (path / "output/MEMORY.md").write_text(
            "# Memory Index\n- [Testing](topics/testing.md) — Test workflow.\n"
            "- [Deploy](topics/deploy.md) — Deploys.\n")
        result = self.run_quiet(memory.promote, name, True)
        self.assertTrue(result["unattended"])
        self.assertEqual(result["validation"]["added_topics"], 1)
        self.assertEqual(memory.validate(memory.active()[1])["topics"], 2)

    def test_unattended_promotion_rejects_rewriting_an_existing_claim(self):
        self.store_with_topic()
        (self.root / "episodes/two.md").write_text("Second claim")
        name, path = self.candidate()
        (path / "output/topics/testing.md").write_text(self.topic(claim="Use Cedar instead."))
        with self.assertRaisesRegex(ValueError, "cannot rewrite existing claims"):
            memory.promote(name, True)
        self.assertNotEqual(memory.active()[0], name)
        # The same candidate remains promotable through the attended lane.
        self.run_quiet(memory.promote, name)
        self.assertEqual(memory.active()[0], name)

    def test_unattended_promotion_rejects_deletion_and_index_rewrite(self):
        self.store_with_topic()
        (self.root / "episodes/two.md").write_text("Second claim")
        name, path = self.candidate()
        (path / "output/topics/testing.md").unlink()
        (path / "output/MEMORY.md").write_text("# Memory Index\n")
        with self.assertRaisesRegex(ValueError, "cannot remove"):
            memory.promote(name, True)
        # A structurally valid index that rewords an existing link is still a rewrite.
        (path / "output/topics/testing.md").write_text(self.topic())
        (path / "output/MEMORY.md").write_text(
            "# Memory Index\n- [Testing](topics/testing.md) — Reworded description.\n")
        with self.assertRaisesRegex(ValueError, "cannot rewrite index lines"):
            memory.promote(name, True)
        self.assertEqual(memory.active()[0], self.store)

    def test_unattended_promotion_rejects_topic_metadata_change(self):
        self.store_with_topic()
        (self.root / "episodes/two.md").write_text("Second claim")
        name, path = self.candidate()
        (path / "output/topics/testing.md").write_text(
            self.topic().replace("type: project", "type: insight"))
        with self.assertRaisesRegex(ValueError, "cannot change topic metadata"):
            memory.promote(name, True)

    def test_status_reports_cadence_and_compaction_signals(self):
        first = self.run_quiet(memory.status)
        self.assertIsNone(first["hours_since_consolidation"])
        self.assertFalse(first["unattended_recommended"])
        for index in range(memory.UNATTENDED_MIN_EPISODES):
            (self.root / f"episodes/e{index}.md").write_text(f"Claim {index}")
        # Never consolidated: the cadence floor does not block the first run.
        self.assertTrue(self.run_quiet(memory.status)["unattended_recommended"])
        name = self.store_with_topic()
        after = self.run_quiet(memory.status)
        self.assertEqual(after["version"], name)
        self.assertEqual(after["unattended_streak"], 1)
        self.assertEqual(after["topics"], 1)
        self.assertLess(after["hours_since_consolidation"], 1)
        self.assertFalse(after["unattended_recommended"])  # Inside the cadence window.
        self.assertFalse(after["compaction_recommended"])

    def test_attended_promotion_leaves_no_unattended_marker(self):
        (self.root / "episodes/one.md").write_text("First claim")
        name, _ = self.candidate()
        self.run_quiet(memory.promote, name)
        self.assertFalse((self.root / "dreams" / name / "unattended").exists())
        self.assertEqual(self.run_quiet(memory.status)["unattended_streak"], 0)

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
