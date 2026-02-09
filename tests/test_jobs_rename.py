"""Test that scheduler has been properly renamed to jobs."""
import unittest
from pathlib import Path


class TestJobsRename(unittest.TestCase):
    """Test that scheduler has been properly renamed to jobs."""

    def test_jobs_directory_exists(self):
        """Test that the jobs directory constant points to the correct location."""
        from miniclaw.core.constants import JOBS_DIR, WORKSPACE_DIR
        self.assertEqual(JOBS_DIR, WORKSPACE_DIR / "jobs")
        self.assertTrue("jobs" in str(JOBS_DIR))

    def test_jobs_py_file_exists(self):
        """Test that jobs.py file exists (renamed from scheduler.py)."""
        jobs_py_path = Path(__file__).parent.parent / "miniclaw" / "data" / "jobs.py"
        self.assertTrue(jobs_py_path.exists(), f"Expected {jobs_py_path} to exist")

    def test_jobs_page_exists(self):
        """Test that JobsPage.jsx file exists (renamed from SchedulerPage.jsx)."""
        jobs_page_path = Path(__file__).parent.parent / "frontend" / "src" / "pages" / "JobsPage.jsx"
        self.assertTrue(jobs_page_path.exists(), f"Expected {jobs_page_path} to exist")

    def test_no_scheduler_py_file(self):
        """Test that scheduler.py file no longer exists."""
        scheduler_py_path = Path(__file__).parent.parent / "miniclaw" / "scheduler.py"
        self.assertFalse(scheduler_py_path.exists(), f"Expected {scheduler_py_path} to not exist")

    def test_no_scheduler_page(self):
        """Test that SchedulerPage.jsx file no longer exists."""
        scheduler_page_path = Path(__file__).parent.parent / "frontend" / "src" / "pages" / "SchedulerPage.jsx"
        self.assertFalse(scheduler_page_path.exists(), f"Expected {scheduler_page_path} to not exist")


if __name__ == "__main__":
    unittest.main()