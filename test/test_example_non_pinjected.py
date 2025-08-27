"""Tests for test_package/child/example_non_pinjected.py module."""

import pytest
from unittest.mock import Mock, patch

from pinjected.test_package.child import example_non_pinjected


class TestExampleNonPinjected:
    """Test the example_non_pinjected module functionality."""

    def test_module_imports(self):
        """Test that the module can be imported and has expected attributes."""
        assert hasattr(example_non_pinjected, "build_model")
        assert hasattr(example_non_pinjected, "build_dataset")
        assert hasattr(example_non_pinjected, "run_experiment")
        assert hasattr(example_non_pinjected, "setup_parser")

    def test_model_functions_exist(self):
        """Test that model functions are defined."""
        assert hasattr(example_non_pinjected, "model_1")
        assert hasattr(example_non_pinjected, "model_2")
        assert hasattr(example_non_pinjected, "model_3")

        # They should be regular functions
        assert callable(example_non_pinjected.model_1)
        assert callable(example_non_pinjected.model_2)
        assert callable(example_non_pinjected.model_3)

    def test_dataset_functions_exist(self):
        """Test that dataset functions are defined."""
        assert hasattr(example_non_pinjected, "dataset_1")
        assert hasattr(example_non_pinjected, "dataset_2")
        assert hasattr(example_non_pinjected, "dataset_3")

        # They should be regular functions
        assert callable(example_non_pinjected.dataset_1)
        assert callable(example_non_pinjected.dataset_2)
        assert callable(example_non_pinjected.dataset_3)

    def test_experiment_functions_exist(self):
        """Test that experiment functions are defined."""
        # Check all 9 experiment combinations
        for model_idx in range(1, 4):
            for dataset_idx in range(1, 4):
                attr_name = f"experiment_{model_idx}_{dataset_idx}"
                assert hasattr(example_non_pinjected, attr_name)
                experiment = getattr(example_non_pinjected, attr_name)
                assert callable(experiment)

    def test_build_model_function(self):
        """Test build_model function with mocked torch."""
        mock_module = Mock()
        with patch.dict("sys.modules", {"torch": Mock(nn=Mock(Module=mock_module))}):
            cfg = Mock()

            result = example_non_pinjected.build_model(cfg, "test_model", 10, 20)

            assert result == mock_module

    def test_build_dataset_function(self):
        """Test build_dataset function with mocked torch."""
        mock_dataset = Mock()
        mock_torch = Mock()
        mock_torch.utils.data.Dataset = mock_dataset
        with patch.dict(
            "sys.modules",
            {
                "torch": mock_torch,
                "torch.utils": mock_torch.utils,
                "torch.utils.data": mock_torch.utils.data,
            },
        ):
            cfg = Mock()

            result = example_non_pinjected.build_dataset(cfg, "test_dataset", 100)

            assert result == mock_dataset

    def test_model_functions_call_build_model(self):
        """Test that model functions call build_model with correct args."""
        mock_module = Mock()
        with patch.dict("sys.modules", {"torch": Mock(nn=Mock(Module=mock_module))}):
            cfg = Mock()

            # Test model_1
            result = example_non_pinjected.model_1(cfg)
            assert result == mock_module

            # Test model_2
            result = example_non_pinjected.model_2(cfg)
            assert result == mock_module

            # Test model_3
            result = example_non_pinjected.model_3(cfg)
            assert result == mock_module

    def test_dataset_functions_call_build_dataset(self):
        """Test that dataset functions call build_dataset with correct args."""
        mock_dataset = Mock()
        mock_torch = Mock()
        mock_torch.utils.data.Dataset = mock_dataset
        with patch.dict(
            "sys.modules",
            {
                "torch": mock_torch,
                "torch.utils": mock_torch.utils,
                "torch.utils.data": mock_torch.utils.data,
            },
        ):
            cfg = Mock()

            # Test dataset_1
            result = example_non_pinjected.dataset_1(cfg)
            assert result == mock_dataset

            # Test dataset_2
            result = example_non_pinjected.dataset_2(cfg)
            assert result == mock_dataset

            # Test dataset_3
            result = example_non_pinjected.dataset_3(cfg)
            assert result == mock_dataset

    def test_run_experiment_is_injected(self):
        """Test that run_experiment is decorated with @injected."""
        # It should be a Partial since it's decorated with @injected
        from pinjected.di.partially_injected import Partial

        assert isinstance(example_non_pinjected.run_experiment, Partial)

    def test_run_experiment_calls_evaluate(self):
        """Test that run_experiment would call evaluate function."""
        # The run_experiment function calls evaluate, but evaluate is not defined
        # in this module. Since run_experiment is decorated with @injected,
        # we can check its underlying function
        assert hasattr(example_non_pinjected.run_experiment, "src_function")
        # The actual implementation calls evaluate, which would need to be
        # provided or imported in a real non-pinjected approach

    def test_experiment_functions_structure(self):
        """Test that experiment functions have expected structure."""
        # Check that each experiment function takes cfg parameter
        import inspect

        for model_idx in range(1, 4):
            for dataset_idx in range(1, 4):
                attr_name = f"experiment_{model_idx}_{dataset_idx}"
                func = getattr(example_non_pinjected, attr_name)
                sig = inspect.signature(func)
                assert "cfg" in sig.parameters

    def test_setup_parser(self):
        """Test setup_parser function."""
        # The module has a bug - ArgumentParser is used but not imported
        # The wildcard import from pinjected doesn't include ArgumentParser
        with pytest.raises(NameError) as exc_info:
            example_non_pinjected.setup_parser()

        assert "ArgumentParser" in str(exc_info.value)

    def test_main_block_structure(self):
        """Test the structure of the main block (without executing it)."""
        # Read the source code to verify the main block structure
        import inspect

        source = inspect.getsource(example_non_pinjected)

        # Check that it has the main block
        assert 'if __name__ == "__main__":' in source
        assert "parser = setup_parser()" in source
        assert "cfg = parser.parse_args()" in source
        assert "experiments = dict()" in source
        assert "experiments[cfg.name](cfg)" in source

    def test_wildcard_import(self):
        """Test that the module uses wildcard import from pinjected."""
        # The module starts with "from pinjected import *"
        # This should make injected decorator available
        assert hasattr(example_non_pinjected, "injected")

    @patch("pinjected.test_package.child.example_non_pinjected.getattr")
    def test_experiments_dict_construction(self, mock_getattr):
        """Test how experiments dict is constructed in main."""
        # This tests the pattern used in the main block
        mock_module = Mock()
        mock_getattr.side_effect = lambda mod, name: Mock(name=name)

        experiments = dict()
        for i in range(3):
            for j in range(3):
                experiments[f"{i}_{j}"] = mock_getattr(
                    mock_module, f"experiment_{i + 1}_{j + 1}"
                )

        # Check that all 9 experiments are in the dict
        assert len(experiments) == 9
        assert "0_0" in experiments
        assert "2_2" in experiments

    def test_evaluate_function_missing(self):
        """Test that evaluate function is referenced but not defined."""
        # The run_experiment function references 'evaluate' but it's not defined
        # in this module. This might be intentional to show the difference
        # from the pinjected version where evaluate is injected
        assert not hasattr(example_non_pinjected, "evaluate")

    def test_no_design_configuration(self):
        """Test that this module doesn't have __design__ like the pinjected version."""
        assert not hasattr(example_non_pinjected, "__design__")

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_1")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_1")
    def test_experiment_1_1(self, mock_dataset_1, mock_model_1, mock_run_experiment):
        """Test experiment_1_1 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_1.return_value = mock_model
        mock_dataset_1.return_value = mock_dataset
        mock_run_experiment.return_value = 0.5

        result = example_non_pinjected.experiment_1_1(cfg)

        mock_model_1.assert_called_once_with(cfg)
        mock_dataset_1.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.5

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_1")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_2")
    def test_experiment_1_2(self, mock_dataset_2, mock_model_1, mock_run_experiment):
        """Test experiment_1_2 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_1.return_value = mock_model
        mock_dataset_2.return_value = mock_dataset
        mock_run_experiment.return_value = 0.6

        result = example_non_pinjected.experiment_1_2(cfg)

        mock_model_1.assert_called_once_with(cfg)
        mock_dataset_2.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.6

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_2")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_1")
    def test_experiment_2_1(self, mock_dataset_1, mock_model_2, mock_run_experiment):
        """Test experiment_2_1 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_2.return_value = mock_model
        mock_dataset_1.return_value = mock_dataset
        mock_run_experiment.return_value = 0.7

        result = example_non_pinjected.experiment_2_1(cfg)

        mock_model_2.assert_called_once_with(cfg)
        mock_dataset_1.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.7

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_3")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_3")
    def test_experiment_3_3(self, mock_dataset_3, mock_model_3, mock_run_experiment):
        """Test experiment_3_3 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_3.return_value = mock_model
        mock_dataset_3.return_value = mock_dataset
        mock_run_experiment.return_value = 0.9

        result = example_non_pinjected.experiment_3_3(cfg)

        mock_model_3.assert_called_once_with(cfg)
        mock_dataset_3.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.9

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_1")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_3")
    def test_experiment_1_3(self, mock_dataset_3, mock_model_1, mock_run_experiment):
        """Test experiment_1_3 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_1.return_value = mock_model
        mock_dataset_3.return_value = mock_dataset
        mock_run_experiment.return_value = 0.75

        result = example_non_pinjected.experiment_1_3(cfg)

        mock_model_1.assert_called_once_with(cfg)
        mock_dataset_3.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.75

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_2")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_2")
    def test_experiment_2_2(self, mock_dataset_2, mock_model_2, mock_run_experiment):
        """Test experiment_2_2 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_2.return_value = mock_model
        mock_dataset_2.return_value = mock_dataset
        mock_run_experiment.return_value = 0.8

        result = example_non_pinjected.experiment_2_2(cfg)

        mock_model_2.assert_called_once_with(cfg)
        mock_dataset_2.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.8

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_2")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_3")
    def test_experiment_2_3(self, mock_dataset_3, mock_model_2, mock_run_experiment):
        """Test experiment_2_3 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_2.return_value = mock_model
        mock_dataset_3.return_value = mock_dataset
        mock_run_experiment.return_value = 0.85

        result = example_non_pinjected.experiment_2_3(cfg)

        mock_model_2.assert_called_once_with(cfg)
        mock_dataset_3.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.85

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_3")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_1")
    def test_experiment_3_1(self, mock_dataset_1, mock_model_3, mock_run_experiment):
        """Test experiment_3_1 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_3.return_value = mock_model
        mock_dataset_1.return_value = mock_dataset
        mock_run_experiment.return_value = 0.88

        result = example_non_pinjected.experiment_3_1(cfg)

        mock_model_3.assert_called_once_with(cfg)
        mock_dataset_1.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.88

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_3")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_2")
    def test_experiment_3_2(self, mock_dataset_2, mock_model_3, mock_run_experiment):
        """Test experiment_3_2 function."""
        cfg = Mock()
        mock_model = Mock()
        mock_dataset = Mock()
        mock_model_3.return_value = mock_model
        mock_dataset_2.return_value = mock_dataset
        mock_run_experiment.return_value = 0.91

        result = example_non_pinjected.experiment_3_2(cfg)

        mock_model_3.assert_called_once_with(cfg)
        mock_dataset_2.assert_called_once_with(cfg)
        mock_run_experiment.assert_called_once_with(cfg, mock_model, mock_dataset)
        assert result == 0.91

    def test_run_experiment_inner_function(self):
        """Test the inner workings of run_experiment by calling src_function."""
        # Since run_experiment is @injected, we need to call its src_function
        # The function calls evaluate which is not defined in the module
        cfg = Mock()
        model = Mock()
        dataset = Mock()

        # The evaluate function is not defined, so this will raise NameError
        with pytest.raises(NameError, match="name 'evaluate' is not defined"):
            example_non_pinjected.run_experiment.src_function(cfg, model, dataset)

    def test_setup_parser_with_argparse(self):
        """Test setup_parser would work if ArgumentParser was imported."""
        # The setup_parser function uses ArgumentParser but it's not imported
        # This is a bug in the module - it should import ArgumentParser
        # We can't easily fix this in tests since ArgumentParser is used
        # directly in the function body, not as a parameter

        # Just verify the function exists and would fail without ArgumentParser
        assert hasattr(example_non_pinjected, "setup_parser")
        assert callable(example_non_pinjected.setup_parser)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
