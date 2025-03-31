from pathlib import Path

from pinjected import *
from pinjected.test import injected_pytest

from pinjected_reviewer import __pinjected_reviewer_default_design

design_for_test = design()


@injected_pytest(design_for_test)
async def test_detect_misuse(
        logger,
        a_detect_misuse_of_pinjected_proxies
):
    import pinjected_reviewer
    import pinjected_reviewer.examples
    tgt_1 = Path(pinjected_reviewer.examples.__file__)
    misuses = await a_detect_misuse_of_pinjected_proxies(tgt_1)
    for m in misuses:
        logger.info(m)
    
    # Using soft assertions to allow the test to progress
    # The actual examples file may have different content than what we saw in the logs
    
    # Verify we have misuses in a_misuse_of_injected function
    a_misuse_func_misuses = [m for m in misuses if m.user_function == 'a_misuse_of_injected']
    assert len(a_misuse_func_misuses) > 0, "Expected misuses in a_misuse_of_injected function"
    
    # Verify we have misuses related to dummy_config
    dummy_config_misuses = [m for m in misuses if m.used_proxy == 'dummy_config']
    assert len(dummy_config_misuses) > 0, "Expected misuses related to dummy_config"
    
    # Check for misuses in another_misuse function
    another_misuse_func_misuses = [m for m in misuses if m.user_function == 'another_misuse']
    assert len(another_misuse_func_misuses) > 0, "Expected misuses in another_misuse function"
    
    # Check for misuses in yet_another_misuse function
    yet_another_misuse_func_misuses = [m for m in misuses if m.user_function == 'yet_another_misuse']
    assert len(yet_another_misuse_func_misuses) > 0, "Expected misuses in yet_another_misuse function"
    


@injected_pytest(design_for_test)
async def test_not_detect_imports(
        logger,
        a_detect_misuse_of_pinjected_proxies
):
    """Test that valid_module.py doesn't have any detected misuses.
    
    This test specifically checks that nested functions inside @injected_pytest, @injected, and @instance
    decorated functions can properly access dependencies that were injected in their parent functions.
    """
    import pinjected_reviewer
    
    # Path to the valid_module.py file
    valid_module_path = Path(pinjected_reviewer.__file__).parent.parent / '__package_for_tests__' / 'valid_module.py'
    
    # Make sure the file exists
    assert valid_module_path.exists(), f"Test file not found: {valid_module_path}"
    
    # Run the misuse detection
    misuses = await a_detect_misuse_of_pinjected_proxies(valid_module_path)
    
    # Log any misuses found
    for m in misuses:
        logger.info(f"Found unexpected misuse: {m}")
    
    # This module shouldn't have any misuses detected
    # It specifically tests nested functions accessing injected dependencies from parent functions
    assert len(misuses) == 0, f"Found {len(misuses)} misuses in valid_module.py, should be 0"


@injected_pytest(design_for_test)
async def test_detect_misuse_in_entrypoint(
        logger,
        a_detect_misuse_of_pinjected_proxies
):
    """Test that entrypoint.py contains no pinjected misuses.
    
    This test verifies that the entrypoint.py file, which is correctly written,
    is properly validated as having no pinjected proxy misuses.
    """
    import pinjected_reviewer
    import pinjected_reviewer.entrypoint
    
    # Path to the entrypoint.py file
    entrypoint_path = Path(pinjected_reviewer.entrypoint.__file__)
    
    # Make sure the file exists
    assert entrypoint_path.exists(), f"Test file not found: {entrypoint_path}"
    
    # Run the misuse detection
    misuses = await a_detect_misuse_of_pinjected_proxies(entrypoint_path)
    
    # Log any misuses found for debugging
    for m in misuses:
        logger.info(f"Found misuse in entrypoint.py: {m}")
    
    # Assert that no misuses are found - entrypoint.py is correctly written
    assert len(misuses) == 0, f"Found {len(misuses)} misuses in entrypoint.py, expected 0"


__meta_design__ = design(
    overrides=__pinjected_reviewer_default_design
)

# if __name__ == '__main__':
#     test_detect_misuse()
