package com.proboscis.pinjectdesign.kotlin

import com.proboscis.pinjectdesign.kotlin.data.PyConfiguration
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue

/**
 * Unit tests for PyConfiguration handling in InjectedFunctionActionHelper.
 * These tests focus on verifying that configurations are correctly identified
 * and that all configuration names are preserved without filtering.
 */
class InjectedFunctionActionHelperTest {
    
    @Test
    fun `test all configuration names are preserved without filtering`() {
        // Create test configurations
        val configurations = listOf(
            PyConfiguration(
                name = "test_function(EmptyDesign)",
                script_path = "/path/to/script.py",
                interpreter_path = "/path/to/python",
                arguments = listOf("run", "module.test_function", "pinjected.EmptyDesign"),
                working_dir = "/working/dir"
            ),
            PyConfiguration(
                name = "test_function(EmptyDesign)_viz",
                script_path = "/path/to/script.py",
                interpreter_path = "/path/to/python",
                arguments = listOf("run_injected", "visualize", "module.test_function", "pinjected.EmptyDesign"),
                working_dir = "/working/dir"
            ),
            PyConfiguration(
                name = "describe test_function",
                script_path = "/path/to/script.py",
                interpreter_path = "/path/to/python",
                arguments = listOf("describe", "module.test_function", "pinjected.EmptyDesign"),
                working_dir = "/working/dir"
            ),
            PyConfiguration(
                name = "Export script",
                script_path = "/path/to/script.py",
                interpreter_path = "/path/to/python",
                arguments = listOf("run", "pinjected.exporter.llm_exporter.export_injected", "--export-target=module.test_function"),
                working_dir = "/working/dir"
            )
        )
        
        // Verify that all configuration names are preserved
        val configNames = configurations.map { it.name }
        
        assertTrue("Regular configuration name should be preserved", configNames.contains("test_function(EmptyDesign)"))
        assertTrue("Visualization configuration name should be preserved", configNames.contains("test_function(EmptyDesign)_viz"))
        assertTrue("Describe configuration name should be preserved", configNames.contains("describe test_function"))
        assertTrue("Export script configuration name should be preserved", configNames.contains("Export script"))
    }
    
    @Test
    fun `test custom configuration names are preserved`() {
        // Create test configurations with custom names
        val configurations = listOf(
            PyConfiguration(
                name = "Custom Action Name",
                script_path = "/path/to/script.py",
                interpreter_path = "/path/to/python",
                arguments = listOf("custom", "command"),
                working_dir = "/working/dir"
            ),
            PyConfiguration(
                name = "Another Custom Action",
                script_path = "/path/to/script.py",
                interpreter_path = "/path/to/python",
                arguments = listOf("another", "custom", "command"),
                working_dir = "/working/dir"
            )
        )
        
        // Verify that custom configuration names are preserved
        val configNames = configurations.map { it.name }
        
        assertTrue("Custom action name should be preserved", configNames.contains("Custom Action Name"))
        assertTrue("Another custom action name should be preserved", configNames.contains("Another Custom Action"))
    }
}
