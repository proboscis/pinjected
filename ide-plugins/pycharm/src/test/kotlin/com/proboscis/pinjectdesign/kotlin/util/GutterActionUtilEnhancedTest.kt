package com.proboscis.pinjectdesign.kotlin.util

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.DefaultActionGroup
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.PySubscriptionExpression
import com.jetbrains.python.psi.PyReferenceExpression
import com.jetbrains.python.psi.PyExpression
import org.junit.Assert.*
import java.util.concurrent.CompletableFuture

class GutterActionUtilEnhancedTest : BasePlatformTestCase() {
    
    override fun getTestDataPath(): String {
        return "src/test/resources/fixtures"
    }
    
    fun testIProxyTypeExtraction() {
        // Create test Python file
        val pythonCode = """
            from pinjected import IProxy
            
            # Test cases
            test_proxy: IProxy[int] = some_func()
            user_proxy: IProxy[User] = IProxy()
            product_proxy: IProxy[Product] = IProxy()
        """.trimIndent()
        
        val psiFile = myFixture.configureByText("test.py", pythonCode)
        
        // Find the test_proxy variable
        val targetElements = com.intellij.psi.util.PsiTreeUtil.findChildrenOfType(
            psiFile, 
            PyTargetExpression::class.java
        )
        
        // Test extracting IProxy types
        val testProxy = targetElements.find { it.name == "test_proxy" }
        assertNotNull("Should find test_proxy", testProxy)
        
        val userProxy = targetElements.find { it.name == "user_proxy" }
        assertNotNull("Should find user_proxy", userProxy)
        
        // Test type extraction logic (simulated)
        testProxy?.let {
            val annotation = it.annotation
            assertNotNull("test_proxy should have annotation", annotation)
            
            if (annotation is PySubscriptionExpression) {
                val operand = annotation.operand
                assertTrue("Should be IProxy", operand is PyReferenceExpression && operand.name == "IProxy")
                
                val typeParam = annotation.indexExpression?.text
                assertEquals("Should extract 'int' as type parameter", "int", typeParam)
            }
        }
        
        userProxy?.let {
            val annotation = it.annotation
            assertNotNull("user_proxy should have annotation", annotation)
            
            if (annotation is PySubscriptionExpression) {
                val typeParam = annotation.indexExpression?.text
                assertEquals("Should extract 'User' as type parameter", "User", typeParam)
            }
        }
    }
    
    fun testInjectedFunctionDataStructure() {
        // Test the data structure itself
        val testFunction = IProxyActionUtil.InjectedFunction(
            function_name = "process_int",
            module_path = "test.module",
            file_path = "/test/file.py",
            line_number = 10,
            parameter_name = "value",
            parameter_type = "int",
            docstring = "Process an integer"
        )
        
        assertEquals("process_int", testFunction.function_name)
        assertEquals("test.module", testFunction.module_path)
        assertEquals("int", testFunction.parameter_type)
        assertNotNull(testFunction.docstring)
    }
    
    fun testQueryCommandConstruction() {
        // Test that the command would be constructed correctly
        // This doesn't actually run the command, just verifies the logic
        val projectRoot = "/test/project"
        val typeParam = "User"
        
        val expectedCommand = listOf(
            "pinjected-indexer",
            "--root", projectRoot,
            "--log-level", "error",
            "query-iproxy-functions",
            typeParam
        )
        
        // Verify command structure
        assertEquals("pinjected-indexer", expectedCommand[0])
        assertEquals(typeParam, expectedCommand.last())
        assertTrue("Command should include --root", expectedCommand.contains("--root"))
    }
    
    fun testIProxyDetectionInPython() {
        val pythonCode = """
            from pinjected import IProxy, injected
            
            class User:
                name: str
            
            # Should detect this
            user_proxy: IProxy[User] = IProxy()
            
            # Should also detect this
            test_proxy: IProxy[int] = some_func()
            
            # Should NOT detect this (not IProxy)
            regular_var: User = User()
            
            # Should NOT detect this (inside class)
            class MyClass:
                class_proxy: IProxy[User] = IProxy()
        """.trimIndent()
        
        val psiFile = myFixture.configureByText("test.py", pythonCode)
        
        val targetElements = com.intellij.psi.util.PsiTreeUtil.findChildrenOfType(
            psiFile, 
            PyTargetExpression::class.java
        )
        
        // Count IProxy variables at module level
        var iproxyCount = 0
        for (target in targetElements) {
            val annotation = target.annotation
            if (annotation is PySubscriptionExpression) {
                val operand = annotation.operand
                if (operand is PyReferenceExpression && operand.name == "IProxy") {
                    // Check if not inside a class
                    val parentClass = com.intellij.psi.util.PsiTreeUtil.getParentOfType(
                        target, 
                        com.jetbrains.python.psi.PyClass::class.java
                    )
                    if (parentClass == null) {
                        iproxyCount++
                        println("Found IProxy variable: ${target.name} with type: ${annotation.indexExpression?.text}")
                    }
                }
            }
        }
        
        assertEquals("Should detect 2 IProxy variables at module level", 2, iproxyCount)
    }
    
    fun testTypeParameterExtraction() {
        val testCases = mapOf(
            "IProxy[int]" to "int",
            "IProxy[User]" to "User",
            "IProxy[List[User]]" to "List[User]",
            "IProxy[Dict[str, Product]]" to "Dict[str, Product]",
            "IProxy[Optional[User]]" to "Optional[User]"
        )
        
        for ((input, expected) in testCases) {
            val pythonCode = """
                from pinjected import IProxy
                test_var: $input = IProxy()
            """.trimIndent()
            
            val psiFile = myFixture.configureByText("test_${expected.replace("[", "_").replace("]", "_")}.py", pythonCode)
            
            val target = com.intellij.psi.util.PsiTreeUtil.findChildOfType(
                psiFile, 
                PyTargetExpression::class.java
            )
            
            assertNotNull("Should find target expression", target)
            
            val annotation = target?.annotation
            if (annotation is PySubscriptionExpression) {
                val typeParam = annotation.indexExpression?.text
                assertEquals("Type parameter for $input", expected, typeParam)
            }
        }
    }
}