import tempfile
import unittest
from pathlib import Path

from orion.memory import ObsidianMemoryBridge
from orion.agents import Dragao, Elias, Pesquisador, Estratega, Documentalista


class BaseAgentTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.memory = ObsidianMemoryBridge(vault_root=self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(str(self.tmpdir))


class TestDragao(BaseAgentTest):
    def setUp(self):
        super().setUp()
        self.dragao = Dragao(self.memory)

    def test_adversarial_review_creates_memory(self):
        entry = self.dragao.adversarial_review("Test hypothesis")
        self.assertIsNotNone(entry.id)
        # Verify it was persisted
        stored = self.memory.read_entry(entry.id)
        self.assertIsNotNone(stored)
        self.assertIn("Avaliação adversarial", stored.content)
        self.assertEqual(stored.tags.get("domain"), "estrategia")


class TestElias(BaseAgentTest):
    def setUp(self):
        super().setUp()
        self.elias = Elias(self.memory)

    def test_research_summary_creates_memory(self):
        entry = self.elias.research_summary("test topic", "some findings")
        stored = self.memory.read_entry(entry.id)
        self.assertIsNotNone(stored)
        self.assertIn("test topic", stored.content)
        self.assertEqual(stored.tags.get("domain"), "avicultura")


class TestPesquisador(BaseAgentTest):
    def setUp(self):
        super().setUp()
        self.pesquisador = Pesquisador(self.memory)

    def test_validate_creates_memory(self):
        entry = self.pesquisador.validate("claim", "reference")
        stored = self.memory.read_entry(entry.id)
        self.assertIsNotNone(stored)
        self.assertIn("Validação", stored.content)


class TestEstratega(BaseAgentTest):
    def setUp(self):
        super().setUp()
        self.estratega = Estratega(self.memory)

    def test_plan_creates_memory(self):
        entry = self.estratega.plan("objective", "steps")
        stored = self.memory.read_entry(entry.id)
        self.assertIsNotNone(stored)


class TestDocumentalista(BaseAgentTest):
    def setUp(self):
        super().setUp()
        self.documentalista = Documentalista(self.memory)

    def test_archive_creates_memory(self):
        entry = self.documentalista.archive("Title", "Summary", scope="system")
        stored = self.memory.read_entry(entry.id)
        self.assertIsNotNone(stored)
        self.assertIn("Summary", stored.content)
        self.assertEqual(stored.tags.get("domain"), "system")


if __name__ == "__main__":
    unittest.main()
