import pytest
import tempfile
from pathlib import Path
import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pinjected_reviewer.reviewer_def import ReviewerDefinition, ReviewerAttributes
from pinjected_reviewer.loader import find_reviewer_markdown_files, simple_extract_reviewer_attributes_fallback

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

@pytest.mark.asyncio
async def test_a_reviewer_definition_from_path():
    content = """# Test Reviewer
    
    This is a test reviewer definition.
    
    
    on commit
    
    
    bool
    """
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        file_path = tmp_path / "test.md"
        file_path.write_text(content)
        
        async def mock_structured_llm(text, response_format=None, **kwargs):
            return ReviewerAttributes(
                Name="Test Reviewer",
                When_to_trigger="on commit",
                Return_Type="bool"
            )
        
        from pinjected_reviewer.loader import a_reviewer_definition_from_path
        
        definition = simple_extract_reviewer_attributes_fallback(
            file_path=file_path,
            content=content
        )
        
        assert definition.name == "Test Reviewer"
        assert definition.trigger_condition == "on commit"
        assert definition.return_type == "bool"
        assert definition.file_path == file_path
        assert definition.raw_content == content

def test_simple_extract_reviewer_attributes_fallback():
    content = """# Test Simple Extractor
    
    
    on push
    
    
    string
    """
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        file_path = tmp_path / "test.md"
        file_path.write_text(content)
        
        definition = simple_extract_reviewer_attributes_fallback(file_path, content)
        
        assert definition.name == "Test Simple Extractor"
        assert definition.trigger_condition == "on push"
        assert definition.return_type == "string"
        assert definition.file_path == file_path
        assert definition.raw_content == content
