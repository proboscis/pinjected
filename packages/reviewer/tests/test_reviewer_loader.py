import pytest
import tempfile
from pathlib import Path
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pinjected_reviewer.reviewer_def import ReviewerDefinition
from pinjected_reviewer.loader import find_reviewer_markdown_files, llm_markdown_extractor

def test_find_reviewer_markdown_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        reviewers_dir = tmp_path / ".reviewers"
        reviewers_dir.mkdir()
        
        (reviewers_dir / "test1.md").write_text("# Test Reviewer 1")
        (reviewers_dir / "test2.md").write_text("# Test Reviewer 2")
        (reviewers_dir / "other.txt").write_text("Not a markdown file")
        
        md_files = find_reviewer_markdown_files(tmp_path)
        assert len(md_files) == 2
        assert set(f.name for f in md_files) == {"test1.md", "test2.md"}

def test_reviewer_definition_from_markdown():
    content = """# Test Reviewer
    
    This is a test reviewer definition.
    
    
    on commit
    
    
    bool
    """
    
    extractor = llm_markdown_extractor()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        file_path = tmp_path / "test.md"
        file_path.write_text(content)
        
        definition = ReviewerDefinition.from_markdown(
            file_path=file_path,
            content=content,
            llm_extractor=extractor
        )
        
        assert definition.name == "Test Reviewer"
        assert definition.trigger_condition == "manual" or definition.trigger_condition == "on commit"
        assert definition.return_type == "bool" or definition.return_type == "None"
        assert definition.file_path == file_path
        assert definition.raw_content == content
