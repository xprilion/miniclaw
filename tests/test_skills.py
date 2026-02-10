"""Unit tests for MiniClaw skills module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from miniclaw.tools.skills import SkillRegistry
from miniclaw.core.events import EventLog


class TestSkillRegistry(unittest.TestCase):
    """Test cases for SkillRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir) / "skills"
        self.event_log = EventLog()
        self.skill_registry = SkillRegistry(self.skills_dir, self.event_log)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test SkillRegistry initialization."""
        self.assertIsInstance(self.skill_registry, SkillRegistry)
        self.assertEqual(self.skill_registry.skills_dir, self.skills_dir)
        # Verify directory was created
        self.assertTrue(self.skills_dir.exists())

    def test_skill_path_valid(self):
        """Test _skill_path with valid skill ID."""
        result = self.skill_registry._skill_path("test-skill")
        # Compare resolved paths to handle macOS /private/var vs /var differences
        self.assertEqual(result.resolve(), (self.skills_dir / "test-skill.md").resolve())

    def test_skill_path_empty_id(self):
        """Test _skill_path with empty skill ID."""
        with self.assertRaises(ValueError) as context:
            self.skill_registry._skill_path("")
        self.assertIn("Skill id is required", str(context.exception))

    def test_skill_path_invalid_characters(self):
        """Test _skill_path with invalid characters."""
        with self.assertRaises(ValueError) as context:
            self.skill_registry._skill_path("test/skill")
        self.assertIn("Skill id may only contain", str(context.exception))

    def test_skill_path_path_traversal(self):
        """Test _skill_path with path traversal attempt."""
        with self.assertRaises(ValueError) as context:
            self.skill_registry._skill_path("../test")
        # The path traversal check happens after the character validation,
        # so we'll get the character validation error first
        self.assertIn(
            "Skill id may only contain lowercase letters, numbers, _ and -",
            str(context.exception),
        )

    def test_title_from_content_with_header(self):
        """Test _title_from_content with markdown header."""
        content = "# Test Skill\n\nThis is a test skill."
        result = self.skill_registry._title_from_content(content, "default")
        self.assertEqual(result, "Test Skill")

    def test_title_from_content_without_header(self):
        """Test _title_from_content without markdown header."""
        content = "This is a test skill without header."
        result = self.skill_registry._title_from_content(content, "default")
        self.assertEqual(result, "default")

    def test_tokens(self):
        """Test _tokens method."""
        text = "This is a test sentence."
        result = self.skill_registry._tokens(text)
        # Should include words with 3+ characters
        self.assertIn("this", result)
        self.assertIn("test", result)
        self.assertIn("sentence", result)
        # Should not include words with < 3 characters
        self.assertNotIn("is", result)
        self.assertNotIn("a", result)

    def test_extract_declared_keywords(self):
        """Test _extract_declared_keywords method."""
        content = "keywords: python, testing, unit\n\n# Test Skill\n\nContent here."
        result = self.skill_registry._extract_declared_keywords(content)
        self.assertIn("python", result)
        self.assertIn("testing", result)
        self.assertIn("unit", result)

    def test_extract_declared_keywords_with_dash_prefix(self):
        """Test _extract_declared_keywords with dash prefix."""
        content = "- keywords: python, testing\n\n# Test Skill\n\nContent here."
        result = self.skill_registry._extract_declared_keywords(content)
        self.assertIn("python", result)
        self.assertIn("testing", result)

    def test_score_skill_relevance_empty_query(self):
        """Test _score_skill_relevance with empty query."""
        skill = {"id": "test", "title": "Test Skill", "content": "Test content"}
        result = self.skill_registry._score_skill_relevance(skill, "")
        self.assertFalse(result["apply"])
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["reason"], "empty_query")

    def test_score_skill_relevance_explicit_id_mention(self):
        """Test _score_skill_relevance with explicit ID mention."""
        skill = {"id": "test-skill", "title": "Test Skill", "content": "Test content"}
        result = self.skill_registry._score_skill_relevance(
            skill, "Use $test-skill for this"
        )
        self.assertTrue(result["apply"])
        self.assertEqual(result["score"], 999)
        self.assertEqual(result["reason"], "explicit_id_mention")

    def test_score_skill_relevance_declared_keyword_match(self):
        """Test _score_skill_relevance with declared keyword match."""
        skill = {
            "id": "test",
            "title": "Test Skill",
            "content": "keywords: python, testing\n\nContent",
        }
        result = self.skill_registry._score_skill_relevance(skill, "I need python help")
        self.assertTrue(result["apply"])
        self.assertEqual(result["score"], 100)
        self.assertIn("declared_keyword", result["reason"])

    def test_score_skill_relevance_token_overlap(self):
        """Test _score_skill_relevance with token overlap."""
        skill = {
            "id": "test",
            "title": "Python Testing",
            "content": "This skill helps with python testing",
        }
        result = self.skill_registry._score_skill_relevance(
            skill, "I need help with python"
        )
        # Should have some score based on token overlap
        self.assertGreaterEqual(result["score"], 0)

    def test_list_empty_directory(self):
        """Test list method with empty directory."""
        result = self.skill_registry.list()
        self.assertEqual(result, [])

    def test_list_with_skills(self):
        """Test list method with existing skills."""
        # Create test skill files
        (self.skills_dir / "test1.md").write_text("# Test Skill 1\n\nContent 1")
        (self.skills_dir / "test2.md").write_text("# Test Skill 2\n\nContent 2")

        result = self.skill_registry.list()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "test1")
        self.assertEqual(result[0]["title"], "Test Skill 1")
        self.assertEqual(result[1]["id"], "test2")
        self.assertEqual(result[1]["title"], "Test Skill 2")

    def test_selected_existing_skills(self):
        """Test selected method with existing skills."""
        # Create test skill file
        (self.skills_dir / "test.md").write_text("# Test Skill\n\nContent")

        result = self.skill_registry.selected(["test"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test")

    def test_selected_nonexistent_skill(self):
        """Test selected method with nonexistent skill."""
        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.selected(["nonexistent"])
            self.assertEqual(result, [])
            # Verify event was logged
            mock_add.assert_called_once()
            self.assertEqual(mock_add.call_args[0][0], "skill.missing")

    def test_applicable_for_query_matching_skill(self):
        """Test applicable_for_query with matching skill."""
        # Create test skill file
        (self.skills_dir / "test.md").write_text(
            "# Test Skill\n\nkeywords: python\n\nContent"
        )

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.applicable_for_query(
                ["test"], "I need python help", 1
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["id"], "test")
            # Verify event was logged
            mock_add.assert_called_with(
                "skill.selected",
                "Skill selected for this query",
                {"skill": "test", "match": result[0]["_match"]},
            )

    def test_applicable_for_query_non_matching_skill(self):
        """Test applicable_for_query with non-matching skill."""
        # Create test skill file
        (self.skills_dir / "test.md").write_text(
            "# Test Skill\n\nContent without matching keywords"
        )

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.applicable_for_query(
                ["test"], "Unrelated query", 100
            )
            self.assertEqual(len(result), 0)
            # Verify event was logged
            mock_add.assert_called_once()
            args, kwargs = mock_add.call_args
            self.assertEqual(args[0], "skill.skipped")
            self.assertEqual(args[1], "Skill skipped for this query")
            self.assertEqual(args[2]["skill"], "test")
            self.assertEqual(args[2]["min_score"], 100)
            # Verify the match object has the expected structure
            match_obj = args[2]["match"]
            self.assertFalse(match_obj["apply"])
            self.assertEqual(match_obj["score"], 0)
            self.assertEqual(match_obj["reason"], "token_overlap")
            self.assertIn("title_overlap", match_obj)
            self.assertIn("content_overlap", match_obj)

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.applicable_for_query(
                ["test"], "Unrelated query", 100
            )
            self.assertEqual(len(result), 0)
            # Verify event was logged
            mock_add.assert_called_once()
            args, kwargs = mock_add.call_args
            self.assertEqual(args[0], "skill.skipped")
            self.assertEqual(args[1], "Skill skipped for this query")
            self.assertEqual(args[2]["skill"], "test")
            self.assertEqual(args[2]["min_score"], 100)
            # Verify the match object has the expected structure
            match_obj = args[2]["match"]
            self.assertFalse(match_obj["apply"])
            self.assertEqual(match_obj["score"], 0)
            self.assertEqual(match_obj["reason"], "token_overlap")
            self.assertIn("title_overlap", match_obj)
            self.assertIn("content_overlap", match_obj)

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.applicable_for_query(
                ["test"], "Unrelated query", 100
            )
            self.assertEqual(len(result), 0)
            # Verify event was logged
            mock_add.assert_called_with(
                "skill.skipped",
                "Skill skipped for this query",
                {
                    "skill": "test",
                    "match": {
                        "apply": False,
                        "score": 0,
                        "reason": "token_overlap",
                        "title_overlap": [],
                        "content_overlap": [],
                    },
                    "min_score": 100,
                },
            )

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.applicable_for_query(
                ["test"], "Unrelated query", 100
            )
            self.assertEqual(len(result), 0)

    def test_save_markdown_skill(self):
        """Test save_markdown_skill method."""
        content = "# Test Skill\n\nThis is a test skill."

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.save_markdown_skill("test-skill", content)

            # Verify result
            self.assertEqual(result["id"], "test-skill")
            self.assertEqual(
                result["content"], content + "\n"
            )  # Should add trailing newline

            # Verify file was created
            skill_file = self.skills_dir / "test-skill.md"
            self.assertTrue(skill_file.exists())
            self.assertEqual(skill_file.read_text(), content + "\n")

            # Verify event was logged
            mock_add.assert_called_once()
            self.assertEqual(mock_add.call_args[0][0], "skill.saved")

    def test_delete_skill_existing(self):
        """Test delete_skill with existing skill."""
        # Create test skill file
        skill_file = self.skills_dir / "test.md"
        skill_file.write_text("# Test Skill\n\nContent")

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.delete_skill("test")

            # Verify result
            self.assertEqual(result["id"], "test")
            self.assertFalse(skill_file.exists())

            # Verify event was logged
            mock_add.assert_called_once()
            self.assertEqual(mock_add.call_args[0][0], "skill.deleted")

    def test_delete_skill_nonexistent(self):
        """Test delete_skill with nonexistent skill."""
        with self.assertRaises(ValueError) as context:
            self.skill_registry.delete_skill("nonexistent")
        self.assertIn("Skill file not found", str(context.exception))

    def test_delete_if_exists_existing(self):
        """Test delete_if_exists with existing skill."""
        # Create test skill file
        skill_file = self.skills_dir / "test.md"
        skill_file.write_text("# Test Skill\n\nContent")

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.delete_if_exists("test")

            self.assertTrue(result)  # File existed and was deleted
            self.assertFalse(skill_file.exists())

            # Verify event was logged
            mock_add.assert_called_once()
            self.assertEqual(mock_add.call_args[0][0], "skill.deleted")

    def test_delete_if_exists_nonexistent(self):
        """Test delete_if_exists with nonexistent skill."""
        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.delete_if_exists("nonexistent")

            self.assertFalse(result)  # File didn't exist
            mock_add.assert_not_called()

    def test_seed_defaults_new_skills(self):
        """Test seed_defaults with new skills."""
        templates = {
            "test1": "# Test Skill 1\n\nContent 1",
            "test2": "# Test Skill 2\n\nContent 2",
        }

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.seed_defaults(templates)

            # Verify result
            self.assertIn("test1", result)
            self.assertIn("test2", result)

            # Verify files were created
            self.assertTrue((self.skills_dir / "test1.md").exists())
            self.assertTrue((self.skills_dir / "test2.md").exists())

            # Verify file contents
            self.assertEqual(
                (self.skills_dir / "test1.md").read_text(),
                "# Test Skill 1\n\nContent 1\n",
            )
            self.assertEqual(
                (self.skills_dir / "test2.md").read_text(),
                "# Test Skill 2\n\nContent 2\n",
            )

            # Verify events were logged
            self.assertEqual(mock_add.call_count, 2)

    def test_seed_defaults_existing_skills(self):
        """Test seed_defaults with existing skills."""
        # Create existing skill file
        (self.skills_dir / "test1.md").write_text(
            "# Existing Skill\n\nExisting content"
        )

        templates = {
            "test1": "# Test Skill 1\n\nContent 1",  # Already exists
            "test2": "# Test Skill 2\n\nContent 2",  # New skill
        }

        with patch.object(self.event_log, "add") as mock_add:
            result = self.skill_registry.seed_defaults(templates)

            # Only new skill should be created
            self.assertNotIn("test1", result)  # Was already existing
            self.assertIn("test2", result)  # Was newly created

            # Verify existing file wasn't overwritten
            self.assertEqual(
                (self.skills_dir / "test1.md").read_text(),
                "# Existing Skill\n\nExisting content",
            )

            # Verify new file was created
            self.assertTrue((self.skills_dir / "test2.md").exists())

            # Only one event should be logged (for the new skill)
            self.assertEqual(mock_add.call_count, 1)


if __name__ == "__main__":
    unittest.main()
