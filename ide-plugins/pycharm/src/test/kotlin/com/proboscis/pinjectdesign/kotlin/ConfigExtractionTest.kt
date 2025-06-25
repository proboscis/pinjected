package com.proboscis.pinjectdesign.kotlin

import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.proboscis.pinjectdesign.kotlin.data.ConfigurationWrapper
import com.proboscis.pinjectdesign.kotlin.data.PyConfiguration
import org.junit.Test
import java.io.File

/**
 * Test to verify that the plugin can extract configurations from Python modules
 * similar to how pytest tests work.
 */
class ConfigExtractionTest : BasePlatformTestCase() {
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.ConfigExtractionTest")
    
    override fun getTestDataPath(): String {
        return "src/test/resources/testData"
    }
    
    @Test
    fun testExtractConfigurationsFromTestModule() {
        // Create a test Python file with injected functions
        val testContent = """
            from pinjected import injected, instance, IProxy
            from pinjected.di.decorators import injected_function
            
            # Test different types of injected elements
            
            @injected
            def test_injected_func(logger):
                '''A simple injected function'''
                return "injected"
            
            @instance
            def test_instance_func():
                '''An instance function'''
                return "instance"
                
            @injected_function
            def test_decorated_func():
                '''A decorated function'''
                return "decorated"
                
            # IProxy variable
            test_iproxy = IProxy(lambda: "iproxy result")
            
            # Regular variable (should not be detected)
            regular_var = "not injected"
            
            # Injected variable with type annotation
            test_injected_var: Injected[str] = injected.pure("injected var")
        """.trimIndent()
        
        val testFile = myFixture.addFileToProject("test_module.py", testContent)
        val virtualFile = testFile.virtualFile
        val modulePath = virtualFile.path
        
        log.info("Created test file at: $modulePath")
        
        // Create a mock helper to test configuration extraction
        val helper = createTestHelper(myFixture.project, modulePath)
        
        // Test findConfigurations method
        log.info("Testing findConfigurations for module: $modulePath")
        
        try {
            val configs = helper.findConfigurations(modulePath)
            log.info("Found configurations: ${configs.keys}")
            
            // Log each configuration in detail
            configs.forEach { (name, configList) ->
                log.info("Configuration for '$name':")
                configList.forEach { config ->
                    log.info("  - name: ${config.name}")
                    log.info("  - script_path: ${config.script_path}")
                    log.info("  - arguments: ${config.arguments}")
                    log.info("  - interpreter_path: ${config.interpreter_path}")
                    log.info("  - working_dir: ${config.working_dir}")
                }
            }
            
            // Verify we found expected configurations
            assertTrue("Should find test_injected_func", configs.containsKey("test_injected_func"))
            assertTrue("Should find test_instance_func", configs.containsKey("test_instance_func"))
            assertTrue("Should find test_iproxy", configs.containsKey("test_iproxy"))
            
            // Verify regular variables are not included
            assertFalse("Should not find regular_var", configs.containsKey("regular_var"))
            
        } catch (e: Exception) {
            log.error("Error extracting configurations", e)
            fail("Failed to extract configurations: ${e.message}")
        }
    }
    
    @Test
    fun testPythonCommandExecution() {
        // Test that we can execute Python commands similar to how the plugin does
        val helper = createTestHelper(myFixture.project, "")
        
        // Test a simple Python command
        val pythonArgs = listOf("-c", "print('Hello from Python')")
        
        try {
            val output = helper.runPython(pythonArgs)
            log.info("Python output: $output")
            assertTrue("Should contain greeting", output.contains("Hello from Python"))
        } catch (e: Exception) {
            log.error("Error running Python", e)
            fail("Failed to run Python: ${e.message}")
        }
    }
    
    @Test
    fun testMetaMainCommand() {
        // Test the actual meta_main command used by the plugin
        val testModulePath = createTestModuleFile()
        val helper = createTestHelper(myFixture.project, testModulePath)
        
        // Test the exact command the plugin uses
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations $testModulePath".split(" ")
        
        try {
            log.info("Running command: python ${args.joinToString(" ")}")
            val configs = helper.runPythonJson<ConfigurationWrapper>(args)
            log.info("Successfully parsed configurations: ${configs.configs.keys}")
            
            assertTrue("Should have configurations", configs.configs.isNotEmpty())
            
        } catch (e: Exception) {
            log.error("Error running meta_main command", e)
            log.error("This might indicate pinjected is not installed or accessible")
            // Don't fail the test, just log the issue
            log.warn("Skipping test due to environment setup: ${e.message}")
        }
    }
    
    private fun createTestHelper(project: Project, modulePath: String): InjectedFunctionActionHelper {
        // Create a test helper with mocked or real Python interpreter
        return object : InjectedFunctionActionHelper(project) {
            override val interpreterPath: String
                get() = findPythonInterpreter()
                
            // Override to add more logging
            override fun runPython(pythonArgs: List<String>): String {
                log.info("Executing Python with args: $pythonArgs")
                val result = super.runPython(pythonArgs)
                log.info("Python execution result (first 200 chars): ${result.take(200)}")
                return result
            }
            
            override fun findConfigurations(modulePath: String): Map<String, List<PyConfiguration>> {
                log.info("Finding configurations for module: $modulePath")
                val result = super.findConfigurations(modulePath)
                log.info("Found ${result.size} configuration groups")
                return result
            }
        }
    }
    
    private fun findPythonInterpreter(): String {
        // Try to find Python interpreter
        val possiblePaths = listOf(
            "/usr/bin/python3",
            "/usr/local/bin/python3",
            System.getenv("PYTHON_PATH") ?: "",
            "python3", // Fallback to PATH
            "python"   // Last resort
        )
        
        for (path in possiblePaths) {
            if (path.isNotEmpty() && File(path).exists()) {
                log.info("Found Python interpreter at: $path")
                return path
            }
        }
        
        log.warn("Could not find Python interpreter, using 'python3'")
        return "python3"
    }
    
    private fun createTestModuleFile(): String {
        // Create a temporary test module file
        val tempFile = File.createTempFile("test_module", ".py")
        tempFile.writeText("""
            from pinjected import injected, instance, IProxy
            
            @injected
            def sample_injected(logger):
                return "test"
                
            sample_iproxy = IProxy(lambda: "test")
        """.trimIndent())
        
        tempFile.deleteOnExit()
        return tempFile.absolutePath
    }
}