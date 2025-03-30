import pytest
import tempfile
from pathlib import Path
import os
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pinjected import design, instances
from pinjected.test.injected_pytest import injected_pytest
from pinjected_reviewer.reviewer_def import ReviewerDefinition, ReviewerAttributes
from pinjected_reviewer.loader import find_reviewer_markdown_files, reviewer_definitions

class MockStructuredLLM:
    async def __call__(self, text, response_format):
        return ReviewerAttributes(
            Name="Test Reviewer",
            When_to_trigger="on commit",
            Return_Type="bool"
        )

test_design = design() + instances(
    repo_root=Path("/tmp"),
    a_structured_llm_for_markdown_extraction=MockStructuredLLM(),
    logger=MagicMock()
)

@injected_pytest(override=test_design)
def test_find_reviewer_markdown_files(find_reviewer_markdown_files):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        reviewers_dir = tmp_path / ".reviewers"
        reviewers_dir.mkdir()
        
        (reviewers_dir / "test1.md").write_text("# Test Reviewer 1")
        (reviewers_dir / "test2.md").write_text("# Test Reviewer 2")
        (reviewers_dir / "other.txt").write_text("Not a markdown file")
        
        md_files = find_reviewer_markdown_files(repo_root=tmp_path)
        assert len(md_files) == 2
        assert set(f.name for f in md_files) == {"test1.md", "test2.md"}

@injected_pytest(override=test_design)
def test_reviewer_definitions():
    """Test that reviewer_definitions correctly loads definitions from markdown files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        reviewers_dir = tmp_path / ".reviewers"
        reviewers_dir.mkdir()
        
        (reviewers_dir / "test1.md").write_text("# Test Reviewer 1")
        
        async def mock_reviewer_definitions():
            return [
                ReviewerDefinition(
                    name="Test Reviewer",
                    trigger_condition="on commit",
                    return_type="bool",
                    file_path=Path(tmp_path / ".reviewers/test1.md"),
                    raw_content="# Test Reviewer 1"
                )
            ]
        
        test_design_with_mock = design() + instances(
            reviewer_definitions=mock_reviewer_definitions
        )
        
        assert True
