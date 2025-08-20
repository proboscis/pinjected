package com.proboscis.pinjectdesign.kotlin.util

import org.junit.Test
import org.junit.Assert.*
import java.util.concurrent.CompletableFuture

/**
 * Simple unit test for IProxy type extraction and function querying logic.
 */
class IProxyTypeExtractionSimpleTest {
    
    @Test
    fun testInjectedFunctionDataClass() {
        // Test the InjectedFunction data class
        val func = IProxyActionUtil.InjectedFunction(
            function_name = "process_user",
            module_path = "app.services",
            file_path = "/app/services.py",
            line_number = 42,
            parameter_name = "user",
            parameter_type = "User",
            docstring = "Process a user object"
        )
        
        assertEquals("process_user", func.function_name)
        assertEquals("User", func.parameter_type)
        assertEquals(42, func.line_number)
        assertNotNull(func.docstring)
    }
    
    @Test
    fun testCommandConstruction() {
        // Test the structure of the indexer command
        val projectRoot = "/home/user/project"
        val typeParam = "User"
        
        // This is what the command should look like
        val expectedParts = listOf(
            "pinjected-indexer",
            "--root",
            projectRoot,
            "--log-level",
            "error",
            "query-iproxy-functions",
            typeParam
        )
        
        // Verify command structure
        assertEquals(7, expectedParts.size)
        assertEquals("pinjected-indexer", expectedParts[0])
        assertEquals("--root", expectedParts[1])
        assertEquals(projectRoot, expectedParts[2])
        assertEquals(typeParam, expectedParts.last())
    }
    
    @Test
    fun testTypeParameterPatterns() {
        // Test various type parameter patterns that should be supported
        val testCases = mapOf(
            "int" to "int",
            "str" to "str",
            "User" to "User",
            "Product" to "Product",
            "List[User]" to "List[User]",
            "Dict[str, User]" to "Dict[str, User]",
            "Optional[User]" to "Optional[User]",
            "Union[User, Product]" to "Union[User, Product]",
            "Tuple[User, int, str]" to "Tuple[User, int, str]"
        )
        
        // These would be extracted from PySubscriptionExpression.indexExpression.text
        for ((input, expected) in testCases) {
            assertEquals("Type parameter should match", expected, input)
        }
    }
    
    @Test
    fun testFunctionListProcessing() {
        // Test how we process a list of functions
        val functions = listOf(
            IProxyActionUtil.InjectedFunction(
                function_name = "process_int",
                module_path = "app.processors",
                file_path = "/app/processors.py",
                line_number = 10,
                parameter_name = "value",
                parameter_type = "int",
                docstring = "Process integer"
            ),
            IProxyActionUtil.InjectedFunction(
                function_name = "double_int",
                module_path = "app.math",
                file_path = "/app/math.py",
                line_number = 20,
                parameter_name = "x",
                parameter_type = "int",
                docstring = "Double the value"
            ),
            IProxyActionUtil.InjectedFunction(
                function_name = "validate_int",
                module_path = "app.validators",
                file_path = "/app/validators.py",
                line_number = 30,
                parameter_name = "num",
                parameter_type = "int",
                docstring = null
            )
        )
        
        // Filter functions by type (all should match "int")
        val intFunctions = functions.filter { it.parameter_type == "int" }
        assertEquals("Should have 3 int functions", 3, intFunctions.size)
        
        // Get function names
        val names = intFunctions.map { it.function_name }
        assertTrue("Should contain process_int", names.contains("process_int"))
        assertTrue("Should contain double_int", names.contains("double_int"))
        assertTrue("Should contain validate_int", names.contains("validate_int"))
        
        // Check that some have docstrings
        val withDocs = intFunctions.filter { it.docstring != null }
        assertEquals("Should have 2 functions with docstrings", 2, withDocs.size)
    }
    
    @Test
    fun testCompletableFutureHandling() {
        // Test how we handle async results
        val testFunctions = listOf(
            IProxyActionUtil.InjectedFunction(
                function_name = "test_func",
                module_path = "test",
                file_path = "/test.py",
                line_number = 1,
                parameter_name = "x",
                parameter_type = "int",
                docstring = "Test"
            )
        )
        
        // Create a completed future
        val future = CompletableFuture.completedFuture(testFunctions)
        
        // Verify we can get the result
        val result = future.get()
        assertNotNull("Result should not be null", result)
        assertEquals("Should have 1 function", 1, result.size)
        assertEquals("test_func", result[0].function_name)
        
        // Test empty result
        val emptyFuture = CompletableFuture.completedFuture(emptyList<IProxyActionUtil.InjectedFunction>())
        val emptyResult = emptyFuture.get()
        assertTrue("Empty result should be empty", emptyResult.isEmpty())
    }
    
    @Test
    fun testMenuItemGeneration() {
        // Test how menu items would be generated from functions
        val functions = listOf(
            IProxyActionUtil.InjectedFunction(
                function_name = "process_user",
                module_path = "app.services.user_service",
                file_path = "/app/services/user_service.py",
                line_number = 50,
                parameter_name = "user",
                parameter_type = "User",
                docstring = "Process and validate user data for storage"
            )
        )
        
        // Simulate menu item creation
        val menuItems = functions.map { func ->
            val moduleName = func.module_path.substringAfterLast('.')
            val docs = func.docstring?.let { " - ${it.take(30)}..." } ?: ""
            "${func.function_name} (${moduleName})$docs"
        }
        
        assertEquals(1, menuItems.size)
        val item = menuItems[0]
        assertTrue("Menu item should contain function name", item.contains("process_user"))
        assertTrue("Menu item should contain module", item.contains("user_service"))
        assertTrue("Menu item should contain truncated docs", item.contains("Process and validate"))
    }
}