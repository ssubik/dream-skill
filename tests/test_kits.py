"""Guard the two parallel kits: identical implementation, separate memory roots."""
import importlib.util
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
KITS = {"kiro": REPO / ".kiro", "claude": REPO / ".claude"}
SCRIPT = "skills/dream/scripts/memory.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KitTests(unittest.TestCase):
    def test_both_kits_ship_the_same_helper(self):
        bodies = {kit: (root / SCRIPT).read_bytes() for kit, root in KITS.items()}
        self.assertEqual(bodies["kiro"], bodies["claude"],
                         "Kit helpers have drifted; re-copy so both enforce the same rules")

    def test_each_kit_resolves_only_its_own_memory_root(self):
        for kit, root in KITS.items():
            module = load(root / SCRIPT, f"memory_{kit}")
            self.assertEqual(module.ROOT, root / "memory")
            self.assertTrue((module.ROOT / "stores/initial/MEMORY.md").is_file())

    def test_each_kit_documents_its_own_paths_only(self):
        other = {"kiro": ".claude/", "claude": ".kiro/"}
        for kit, root in KITS.items():
            for doc in sorted(root.glob("skills/**/*.md")):
                text = doc.read_text(encoding="utf-8")
                for block in text.split("\n\n"):
                    # A kit may name the other one only to forbid touching it.
                    if other[kit] in block and "never" not in block.lower():
                        self.fail(f"{doc.relative_to(REPO)} points at the other kit:"
                                  f" {block.strip()[:120]}")


if __name__ == "__main__":
    unittest.main()
