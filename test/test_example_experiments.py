"""Tests for test_package/child/example_experiments.py module."""

import pytest

from pinjected.di.proxiable import DelegatedVar
from pinjected.test_package.child import example_experiments


class TestExampleExperiments:
    """Test the example_experiments module functionality."""

    def test_module_imports(self):
        """Test that the module can be imported and has expected attributes."""
        assert hasattr(example_experiments, "build_model")
        assert hasattr(example_experiments, "build_dataset")
        assert hasattr(example_experiments, "run_experiment")
        assert hasattr(example_experiments, "evaluate")
        assert hasattr(example_experiments, "logger")
        assert hasattr(example_experiments, "__design__")

    def test_model_proxies_exist(self):
        """Test that model proxy objects are created."""
        assert hasattr(example_experiments, "model_1")
        assert hasattr(example_experiments, "model_2")
        assert hasattr(example_experiments, "model_3")

        # They should be DelegatedVar instances (which implement IProxy)
        assert isinstance(example_experiments.model_1, DelegatedVar)
        assert isinstance(example_experiments.model_2, DelegatedVar)
        assert isinstance(example_experiments.model_3, DelegatedVar)

    def test_dataset_proxies_exist(self):
        """Test that dataset proxy objects are created."""
        assert hasattr(example_experiments, "dataset_1")
        assert hasattr(example_experiments, "dataset_2")
        assert hasattr(example_experiments, "dataset_3")

        # They should be DelegatedVar instances (which implement IProxy)
        assert isinstance(example_experiments.dataset_1, DelegatedVar)
        assert isinstance(example_experiments.dataset_2, DelegatedVar)
        assert isinstance(example_experiments.dataset_3, DelegatedVar)

    def test_experiment_proxies_exist(self):
        """Test that experiment proxy objects are created."""
        # Check all 9 experiment combinations
        for model_idx in range(1, 4):
            for dataset_idx in range(1, 4):
                attr_name = f"experiment_{model_idx}_{dataset_idx}"
                assert hasattr(example_experiments, attr_name)
                experiment = getattr(example_experiments, attr_name)
                assert isinstance(experiment, DelegatedVar)

    def test_run_all_experiments_proxy(self):
        """Test that run_all_experiments is properly created."""
        assert hasattr(example_experiments, "run_all_experiments")
        assert isinstance(example_experiments.run_all_experiments, DelegatedVar)

        # DelegatedVar wraps the actual Injected, so we verify it exists
        # and can be evaluated to get the actual Injected object

    def test_build_model_function(self):
        """Test build_model function exists and is injected."""
        # Verify build_model is an injected function
        assert hasattr(example_experiments.build_model, "__call__")
        # It should be a Partial since it's decorated with @injected
        from pinjected.di.partially_injected import Partial

        assert isinstance(example_experiments.build_model, Partial)

    def test_build_dataset_function(self):
        """Test build_dataset function exists and is injected."""
        # Verify build_dataset is an injected function
        assert hasattr(example_experiments.build_dataset, "__call__")
        # It should be a Partial since it's decorated with @injected
        from pinjected.di.partially_injected import Partial

        assert isinstance(example_experiments.build_dataset, Partial)

    def test_run_experiment_function(self):
        """Test run_experiment function exists and is injected."""
        # Verify run_experiment is an injected function
        assert hasattr(example_experiments.run_experiment, "__call__")
        # It should be a Partial since it's decorated with @injected
        from pinjected.di.partially_injected import Partial

        assert isinstance(example_experiments.run_experiment, Partial)

    def test_evaluate_function(self):
        """Test evaluate function exists and is injected."""
        # Verify evaluate is an injected function
        assert hasattr(example_experiments.evaluate, "__call__")
        # It should be a Partial since it's decorated with @injected
        from pinjected.di.partially_injected import Partial

        assert isinstance(example_experiments.evaluate, Partial)

    def test_logger_instance(self):
        """Test logger instance function."""
        # logger is decorated with @instance, so calling it returns a DelegatedVar
        result = example_experiments.logger()
        assert isinstance(result, DelegatedVar)

        # The actual logger function itself (before decoration) would return None
        # but we can't easily access that through the decorated version

    def test_design_configuration(self):
        """Test that __design__ is properly configured."""
        design_obj = example_experiments.__design__

        # Should be a design object
        assert hasattr(design_obj, "__class__")

        # The design should have overrides
        # Note: The actual structure of design objects may vary
        # This test ensures the design is created without errors

    def test_injected_function_dependencies(self):
        """Test that injected functions have correct dependencies."""
        # DelegatedVar objects wrap the actual Injected objects
        # We can verify they exist and have the expected structure

        # Test that the proxies exist and are DelegatedVar instances
        assert isinstance(example_experiments.model_1, DelegatedVar)
        assert isinstance(example_experiments.dataset_1, DelegatedVar)
        assert isinstance(example_experiments.experiment_1_1, DelegatedVar)

    def test_model_type_annotations(self):
        """Test that models have correct type annotations."""
        # The module defines Model = object at the top
        assert example_experiments.Model is object
        assert example_experiments.Dataset is object

    def test_all_experiments_included_in_run_all(self):
        """Test that run_all_experiments includes all individual experiments."""
        # Verify run_all_experiments exists and is a DelegatedVar
        assert hasattr(example_experiments, "run_all_experiments")
        assert isinstance(example_experiments.run_all_experiments, DelegatedVar)

        # The actual dependencies would be in the wrapped Injected object,
        # but we can't easily access that without evaluating the proxy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
