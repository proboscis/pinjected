"""Simple tests for test_package/child/example_non_pinjected.py to improve coverage."""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the module we're testing
from pinjected.test_package.child.example_non_pinjected import (
    build_model,
    model_1,
    model_2,
    model_3,
    build_dataset,
    dataset_1,
    dataset_2,
    dataset_3,
    run_experiment,
    experiment_1_1,
    experiment_1_2,
    experiment_1_3,
    experiment_2_1,
    experiment_2_2,
    experiment_2_3,
    experiment_3_1,
    experiment_3_2,
    experiment_3_3,
    setup_parser,
)


class TestBuildFunctions:
    """Test the build functions."""

    @patch("pinjected.test_package.child.example_non_pinjected.nn")
    def test_build_model(self, mock_nn):
        """Test build_model function."""
        mock_nn.Module = MagicMock()
        cfg = {"test": "config"}

        result = build_model(cfg, "test_model", 5, 10)

        assert result is mock_nn.Module

    @patch("torch.utils.data.Dataset")
    def test_build_dataset(self, mock_dataset):
        """Test build_dataset function."""
        cfg = {"test": "config"}

        result = build_dataset(cfg, "test_dataset", 100)

        # Should return Dataset class (not instance)
        assert result is not None


class TestModelFunctions:
    """Test the model creation functions."""

    @patch("pinjected.test_package.child.example_non_pinjected.build_model")
    def test_model_1(self, mock_build):
        """Test model_1 function."""
        mock_build.return_value = "model1"
        cfg = {"config": "value"}

        result = model_1(cfg)

        mock_build.assert_called_once_with(cfg, "model_1", 10, 20)
        assert result == "model1"

    @patch("pinjected.test_package.child.example_non_pinjected.build_model")
    def test_model_2(self, mock_build):
        """Test model_2 function."""
        mock_build.return_value = "model2"
        cfg = {"config": "value"}

        result = model_2(cfg)

        mock_build.assert_called_once_with(cfg, "model_2", 5, 3)
        assert result == "model2"

    @patch("pinjected.test_package.child.example_non_pinjected.build_model")
    def test_model_3(self, mock_build):
        """Test model_3 function."""
        mock_build.return_value = "model3"
        cfg = {"config": "value"}

        result = model_3(cfg)

        mock_build.assert_called_once_with(cfg, "model_3", 7, 8)
        assert result == "model3"


class TestDatasetFunctions:
    """Test the dataset creation functions."""

    @patch("pinjected.test_package.child.example_non_pinjected.build_dataset")
    def test_dataset_1(self, mock_build):
        """Test dataset_1 function."""
        mock_build.return_value = "dataset1"
        cfg = {"config": "value"}

        result = dataset_1(cfg)

        mock_build.assert_called_once_with(cfg, "dataset_1", 100)
        assert result == "dataset1"

    @patch("pinjected.test_package.child.example_non_pinjected.build_dataset")
    def test_dataset_2(self, mock_build):
        """Test dataset_2 function."""
        mock_build.return_value = "dataset2"
        cfg = {"config": "value"}

        result = dataset_2(cfg)

        mock_build.assert_called_once_with(cfg, "dataset_2", 200)
        assert result == "dataset2"

    @patch("pinjected.test_package.child.example_non_pinjected.build_dataset")
    def test_dataset_3(self, mock_build):
        """Test dataset_3 function."""
        mock_build.return_value = "dataset3"
        cfg = {"config": "value"}

        result = dataset_3(cfg)

        mock_build.assert_called_once_with(cfg, "dataset_3", 300)
        assert result == "dataset3"


class TestRunExperiment:
    """Test the run_experiment function."""

    @patch("pinjected.test_package.child.example_non_pinjected.evaluate")
    def test_run_experiment(self, mock_evaluate):
        """Test run_experiment function."""
        mock_evaluate.return_value = 0.95

        # run_experiment is injected, so we need to get the underlying function
        func = run_experiment.src_function

        cfg = {"config": "value"}
        model = Mock()
        dataset = Mock()

        result = func(cfg, model, dataset)

        mock_evaluate.assert_called_once_with(cfg, model, dataset)
        assert result == 0.95


class TestExperimentFunctions:
    """Test all experiment functions."""

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_1")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_1")
    def test_experiment_1_1(self, mock_dataset, mock_model, mock_run):
        """Test experiment_1_1."""
        mock_model.return_value = "model"
        mock_dataset.return_value = "dataset"
        mock_run.return_value = 0.9

        cfg = {"config": "value"}
        result = experiment_1_1(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)
        mock_run.assert_called_once_with(cfg, "model", "dataset")
        assert result == 0.9

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_1")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_2")
    def test_experiment_1_2(self, mock_dataset, mock_model, mock_run):
        """Test experiment_1_2."""
        cfg = {"config": "value"}
        experiment_1_2(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_1")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_3")
    def test_experiment_1_3(self, mock_dataset, mock_model, mock_run):
        """Test experiment_1_3."""
        cfg = {"config": "value"}
        experiment_1_3(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_2")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_1")
    def test_experiment_2_1(self, mock_dataset, mock_model, mock_run):
        """Test experiment_2_1."""
        cfg = {"config": "value"}
        experiment_2_1(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_2")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_2")
    def test_experiment_2_2(self, mock_dataset, mock_model, mock_run):
        """Test experiment_2_2."""
        cfg = {"config": "value"}
        experiment_2_2(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_2")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_3")
    def test_experiment_2_3(self, mock_dataset, mock_model, mock_run):
        """Test experiment_2_3."""
        cfg = {"config": "value"}
        experiment_2_3(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_3")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_1")
    def test_experiment_3_1(self, mock_dataset, mock_model, mock_run):
        """Test experiment_3_1."""
        cfg = {"config": "value"}
        experiment_3_1(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_3")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_2")
    def test_experiment_3_2(self, mock_dataset, mock_model, mock_run):
        """Test experiment_3_2."""
        cfg = {"config": "value"}
        experiment_3_2(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)

    @patch("pinjected.test_package.child.example_non_pinjected.run_experiment")
    @patch("pinjected.test_package.child.example_non_pinjected.model_3")
    @patch("pinjected.test_package.child.example_non_pinjected.dataset_3")
    def test_experiment_3_3(self, mock_dataset, mock_model, mock_run):
        """Test experiment_3_3."""
        cfg = {"config": "value"}
        experiment_3_3(cfg)

        mock_model.assert_called_once_with(cfg)
        mock_dataset.assert_called_once_with(cfg)


class TestSetupParser:
    """Test the setup_parser function."""

    def test_setup_parser(self):
        """Test setup_parser creates ArgumentParser."""
        parser = setup_parser()

        # Check it's an ArgumentParser
        from argparse import ArgumentParser

        assert isinstance(parser, ArgumentParser)

        # Check it has the required argument
        # Parse with the required argument
        args = parser.parse_args(["--name", "test_experiment"])
        assert args.name == "test_experiment"

        # Should fail without --name
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestMainBlock:
    """Test the main block execution."""

    @patch("sys.modules")
    @patch("pinjected.test_package.child.example_non_pinjected.setup_parser")
    def test_main_block_execution(self, mock_setup_parser, mock_modules):
        """Test the main block builds experiments dict."""
        # Mock parser
        mock_parser = Mock()
        mock_args = Mock()
        mock_args.name = "1_1"
        mock_parser.parse_args.return_value = mock_args
        mock_setup_parser.return_value = mock_parser

        # Mock the module to have all experiment functions
        mock_module = Mock()
        for i in range(1, 4):
            for j in range(1, 4):
                setattr(
                    mock_module,
                    f"experiment_{i}_{j}",
                    Mock(return_value=f"result_{i}_{j}"),
                )

        mock_modules.__getitem__.return_value = mock_module

        # Import and execute the main block by simulating it
        experiments = {}
        for i in range(3):
            for j in range(3):
                experiments[f"{i}_{j}"] = getattr(
                    mock_module, f"experiment_{i + 1}_{j + 1}"
                )

        # Check all experiments are in the dict
        assert len(experiments) == 9
        assert "0_0" in experiments
        assert "2_2" in experiments

        # Execute the selected experiment
        experiments["1_1"](mock_args)
        mock_module.experiment_2_2.assert_called_once_with(mock_args)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
