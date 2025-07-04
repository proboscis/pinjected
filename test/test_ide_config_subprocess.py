"""Test IDE config creation via subprocess - testing the exact commands IDEs run.

UPDATE: Fixed the issue where IDE plugins (PyCharm/IntelliJ and VSCode) don't pass design_path.
The run_with_meta_context function now uses pinjected_internal_design by default when
design_path is not provided, ensuring backward compatibility with existing IDE plugins.

These tests verify both behaviors:
1. Without design_path (how IDE plugins actually call it)
2. With explicit design_path (recommended approach)
"""

import json
import sys
import os
import subprocess
from pathlib import Path


class TestSubprocessIntegration:
    """Test IDE commands via subprocess to ensure they work in real usage."""

    def test_subprocess_create_configurations_simple_module(self):
        """Test the exact IDE command to create configurations using a simple module.

        This now matches how IDE plugins actually call the command (without design_path).
        See issue: tasks/20250625-test-ide-config-creation/ide-plugin-migration-issue.md
        """
        # Use the pinjected repo path (parent of test directory)
        pinjected_path = Path(__file__).parent.parent

        # First, let's add pinjected to PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pinjected_path) + os.pathsep + env.get("PYTHONPATH", "")

        # Use the actual test module from pinjected
        test_module_path = pinjected_path / "pinjected/test_package/child/module1.py"

        # Command format matching IDE plugins (NO design_path parameter)
        # See issue: Migrate IDE plugins from meta_main to pinjected run command
        cmd = [
            sys.executable,
            "-m",
            "pinjected.meta_main",
            "pinjected.ide_supports.create_configs.create_idea_configurations",  # var_path
            str(test_module_path),  # context_module_file_path
            # NO design_path - uses default pinjected_internal_design
        ]

        # Run from the pinjected directory
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(pinjected_path), env=env
        )

        # Debug output if it fails
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr[:1000]}...")  # First 1000 chars
            print(f"STDOUT: {result.stdout[:1000]}...")

        # The command should succeed now with the default design fix

        assert result.returncode == 0, (
            f"Command failed with return code {result.returncode}"
        )

        # Parse the output - should contain <pinjected>...</pinjected> tags
        stdout = result.stdout
        assert "<pinjected>" in stdout, "Output should contain <pinjected> tag"
        assert "</pinjected>" in stdout, "Output should contain </pinjected> tag"

        # Extract JSON between tags
        start = stdout.find("<pinjected>") + 11
        end = stdout.find("</pinjected>")
        json_content = stdout[start:end]

        # Parse JSON
        data = json.loads(json_content)
        assert "configs" in data, "JSON should contain 'configs' key"

        configs = data["configs"]
        assert len(configs) > 0, "Should find some configurations"

        # Check that we found some expected entries from test module
        expected_entries = [
            "test_runnable",
            "test_viz_target",
            "a",
            "b",
            "test_function",
            "test_always_failure",
        ]
        found_entries = [key for key in configs if key in expected_entries]

        assert len(found_entries) > 0, (
            f"Should find some expected entries, found: {list(configs.keys())}"
        )

        print(f"✓ Successfully created configurations via subprocess")
        print(f"✓ Found {len(configs)} configurations: {list(configs.keys())[:5]}...")

        # Verify the structure of configurations
        for entry_name in found_entries[:2]:  # Check first 2
            entry_configs = configs[entry_name]
            assert isinstance(entry_configs, list), (
                f"{entry_name} should have a list of configs"
            )
            assert len(entry_configs) > 0, (
                f"{entry_name} should have at least one config"
            )

            config = entry_configs[0]
            assert "name" in config
            assert "script_path" in config
            assert "interpreter_path" in config
            assert "arguments" in config
            assert "working_dir" in config

            # Check command type
            args = config["arguments"]
            if entry_name in ["test_runnable", "a", "b"]:
                assert args[0] == "run", f"IProxy {entry_name} should use 'run' command"

    def test_subprocess_run_extracted_command(self):
        """Test running a command extracted from IDE configurations.

        Uses the IDE plugin command format (without design_path).
        See issue: tasks/20250625-test-ide-config-creation/ide-plugin-migration-issue.md
        """
        pinjected_path = Path(__file__).parent.parent

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pinjected_path) + os.pathsep + env.get("PYTHONPATH", "")

        # Use an actual test module instead of temp file
        test_module_path = pinjected_path / "pinjected/test_package/child/module1.py"

        try:
            # First, get configurations (IDE plugin format - no design_path)
            cmd = [
                sys.executable,
                "-m",
                "pinjected.meta_main",
                "pinjected.ide_supports.create_configs.create_idea_configurations",
                str(test_module_path),
                # NO design_path - matches IDE plugin behavior
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(pinjected_path), env=env
            )
            assert result.returncode == 0, f"Command failed: {result.stderr}"

            # Parse configurations
            stdout = result.stdout
            start = stdout.find("<pinjected>") + 11
            end = stdout.find("</pinjected>")
            json_content = stdout[start:end]
            data = json.loads(json_content)

            # Get the config for test_runnable (an IProxy value we know exists)
            test_runnable_config = data["configs"]["test_runnable"][0]

            # Extract the command arguments
            script_path = test_runnable_config["script_path"]
            arguments = test_runnable_config["arguments"]

            # Run the extracted command
            run_cmd = [sys.executable, script_path] + arguments

            run_result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                cwd=str(pinjected_path),
                env=env,
            )

            # Should succeed and output something
            assert run_result.returncode == 0, (
                f"Run command failed: {run_result.stderr}"
            )

            print(f"✓ Successfully ran extracted command via subprocess")
            print(f"✓ Command output: {run_result.stdout.strip()}")

        finally:
            # No cleanup needed since we're using actual modules
            pass

    def test_subprocess_test_package_module(self):
        """Test creating configurations for the actual test_package module.

        Uses IDE plugin format (no design_path).
        See issue: tasks/20250625-test-ide-config-creation/ide-plugin-migration-issue.md
        """
        pinjected_path = Path(__file__).parent.parent

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pinjected_path) + os.pathsep + env.get("PYTHONPATH", "")

        # Use the actual test module that has IProxy and injected functions
        test_module_path = pinjected_path / "pinjected/test_package/child/module1.py"

        # Run the command (IDE plugin format - no design_path)
        cmd = [
            sys.executable,
            "-m",
            "pinjected.meta_main",
            "pinjected.ide_supports.create_configs.create_idea_configurations",
            str(test_module_path),
            # NO design_path - uses default
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(pinjected_path), env=env
        )

        # Debug output if it fails
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr[:2000]}...")
            print(f"STDOUT: {result.stdout[:2000]}...")

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse output
        stdout = result.stdout
        start = stdout.find("<pinjected>") + 11
        end = stdout.find("</pinjected>")
        json_content = stdout[start:end]

        data = json.loads(json_content)
        configs = data["configs"]

        # Verify we found expected entries from module1.py
        expected_entries = [
            "test_runnable",  # IProxy
            "run_test",  # IProxy
            "test_viz_target",  # @instance function
            "test_function",  # @injected function
            "a",
            "b",  # IProxy values
        ]

        found_entries = [key for key in expected_entries if key in configs]
        assert len(found_entries) > 0, (
            f"Should find some expected entries, found: {list(configs.keys())}"
        )

        # Check that IProxy entries use "run" command
        iproxy_entries = ["test_runnable", "run_test", "a", "b"]
        for entry in iproxy_entries:
            if entry in configs:
                config = configs[entry][0]
                args = config["arguments"]
                if args:  # Check if args is not empty
                    assert args[0] == "run", (
                        f"{entry} should use 'run' command, got: {args}"
                    )

        # Check configuration structure
        print(f"\n✓ Successfully created configurations for test_package module")
        print(f"✓ Found {len(configs)} configurations")
        print(f"✓ Found expected entries: {found_entries}")

        # Check that some entries have the custom config from dummy_config_creator_for_test
        if "dummy for test_package.child.__init__" in str(configs):
            print("✓ Custom config creator was called")

    def test_subprocess_with_explicit_design_path(self):
        """Test that explicitly passing design_path still works.

        This ensures backward compatibility for users who explicitly specify design_path.
        See issue: tasks/20250625-test-ide-config-creation/ide-plugin-migration-issue.md
        """
        pinjected_path = Path(__file__).parent.parent

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(pinjected_path) + os.pathsep + env.get("PYTHONPATH", "")

        # Use the actual test module
        test_module_path = pinjected_path / "pinjected/test_package/child/module1.py"

        # Command WITH explicit design_path - testing backward compatibility
        cmd = [
            sys.executable,
            "-m",
            "pinjected.meta_main",
            "pinjected.ide_supports.create_configs.create_idea_configurations",
            str(test_module_path),
            "pinjected.ide_supports.default_design.pinjected_internal_design",  # Explicit design_path
        ]

        # Run from the pinjected directory
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(pinjected_path), env=env
        )

        # Debug output if it fails
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr[:1000]}...")
            print(f"STDOUT: {result.stdout[:1000]}...")

        # The command should now succeed with the default design
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Should NOT see the warning when design_path is explicitly provided
        assert "No design_path provided" not in result.stderr, (
            "Should not warn about default design when explicitly provided"
        )

        # Parse the output - should still work
        stdout = result.stdout
        assert "<pinjected>" in stdout, "Output should contain <pinjected> tag"
        assert "</pinjected>" in stdout, "Output should contain </pinjected> tag"

        # Extract JSON between tags
        start = stdout.find("<pinjected>") + 11
        end = stdout.find("</pinjected>")
        json_content = stdout[start:end]

        # Parse JSON
        data = json.loads(json_content)
        assert "configs" in data, "JSON should contain 'configs' key"

        configs = data["configs"]
        assert len(configs) > 0, (
            "Should find some configurations with explicit design_path"
        )

        print(f"✓ Successfully created configurations WITH explicit design_path")
        print(f"✓ Found {len(configs)} configurations")
        print(f"✓ Backward compatibility maintained for explicit design_path usage")
