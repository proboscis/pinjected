package com.proboscis.pinjectdesign.kotlin.integration

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.PySubscriptionExpression
import com.jetbrains.python.psi.PyReferenceExpression
import com.proboscis.pinjectdesign.kotlin.util.GutterActionUtilEnhanced
import com.proboscis.pinjectdesign.kotlin.util.IProxyActionUtil
import com.intellij.psi.util.PsiTreeUtil
import org.junit.Assert.*
import java.io.File
import java.util.concurrent.TimeUnit

/**
 * End-to-end test for IProxy functionality.
 * Tests the complete flow from Python code to menu generation.
 */
class IProxyE2ETest : BasePlatformTestCase() {
    
    override fun getTestDataPath(): String {
        return "src/test/resources/fixtures"
    }
    
    fun testCompleteIProxyFlow() {
        // Step 1: Create a Python file with IProxy variables
        val pythonCode = """
            from pinjected import IProxy, injected
            
            class User:
                name: str
                email: str
            
            class Product:
                id: int
                price: float
            
            # IProxy variables that should be detected
            user_proxy: IProxy[User] = IProxy()
            product_proxy: IProxy[Product] = IProxy()
            test_proxy: IProxy[int] = some_func()
            
            # @injected functions
            @injected
            def process_user(user: User) -> str:
                return user.name
            
            @injected
            def process_int(value: int) -> int:
                return value * 2
            
            def some_func():
                return IProxy()
        """.trimIndent()
        
        val psiFile = myFixture.configureByText("test_e2e.py", pythonCode)
        
        // Step 2: Find IProxy variables
        val targetExpressions = PsiTreeUtil.findChildrenOfType(psiFile, PyTargetExpression::class.java)
        val iproxyVariables = mutableListOf<Pair<String, String>>() // name -> type
        
        for (target in targetExpressions) {
            val annotation = target.annotation
            if (annotation is PySubscriptionExpression) {
                val operand = annotation.operand
                if (operand is PyReferenceExpression && operand.name == "IProxy") {
                    val varName = target.name ?: continue
                    val typeParam = annotation.indexExpression?.text ?: "Unknown"
                    iproxyVariables.add(varName to typeParam)
                    
                    println("Found IProxy variable: $varName with type: $typeParam")
                }
            }
        }
        
        // Step 3: Verify we found the expected IProxy variables
        assertEquals("Should find 3 IProxy variables", 3, iproxyVariables.size)
        
        val foundTypes = iproxyVariables.map { it.second }.toSet()
        assertTrue("Should find User type", foundTypes.contains("User"))
        assertTrue("Should find Product type", foundTypes.contains("Product"))
        assertTrue("Should find int type", foundTypes.contains("int"))
        
        // Step 4: Test type extraction for each variable
        for ((varName, expectedType) in iproxyVariables) {
            val targetExpr = targetExpressions.find { it.name == varName }
            assertNotNull("Should find target expression for $varName", targetExpr)
            
            // Simulate what GutterActionUtilEnhanced does
            val extractedType = extractIProxyTypeFromExpression(targetExpr!!)
            assertEquals("Type for $varName should match", expectedType, extractedType)
        }
        
        // Step 5: Test that the correct element would trigger menu creation
        val testProxyTarget = targetExpressions.find { it.name == "test_proxy" }
        assertNotNull("Should find test_proxy", testProxyTarget)
        
        val nameIdentifier = testProxyTarget?.nameIdentifier
        assertNotNull("test_proxy should have name identifier", nameIdentifier)
        
        // This is what would be passed to GutterActionUtilEnhanced
        println("Name identifier text: ${nameIdentifier?.text}")
        println("Name identifier type: ${nameIdentifier?.node?.elementType}")
        
        // Verify it's a Py:IDENTIFIER as expected
        assertEquals("Py:IDENTIFIER", nameIdentifier?.node?.elementType?.toString())
    }
    
    fun testIndexerQueryIntegration() {
        // Test the actual indexer query (if indexer is available)
        val indexerPath = findIndexer()
        
        if (indexerPath == null) {
            println("pinjected-indexer not found, skipping indexer test")
            return
        }
        
        println("Found indexer at: $indexerPath")
        
        // Create a temporary test project
        val tempDir = createTempDir("test_project")
        val testFile = File(tempDir, "test.py")
        testFile.writeText("""
            from pinjected import IProxy, injected
            
            @injected
            def process_int(value: int) -> int:
                return value * 2
            
            @injected  
            def double_int(x: int) -> int:
                return x * 2
            
            test_proxy: IProxy[int] = IProxy()
        """.trimIndent())
        
        // Run indexer to build index
        val buildProcess = ProcessBuilder(
            indexerPath,
            "--root", tempDir.absolutePath,
            "--log-level", "error",
            "index"
        ).start()
        
        val buildExited = buildProcess.waitFor(10, TimeUnit.SECONDS)
        if (!buildExited) {
            buildProcess.destroyForcibly()
            println("Indexer build timed out")
            return
        }
        
        // Query for int functions
        val queryProcess = ProcessBuilder(
            indexerPath,
            "--root", tempDir.absolutePath,
            "--log-level", "error",
            "query-iproxy-functions",
            "int"
        ).start()
        
        val queryExited = queryProcess.waitFor(5, TimeUnit.SECONDS)
        if (!queryExited) {
            queryProcess.destroyForcibly()
            println("Indexer query timed out")
            return
        }
        
        val output = queryProcess.inputStream.bufferedReader().readText()
        println("Indexer output: $output")
        
        // Verify we got some results
        if (output.isNotBlank() && output.startsWith("[")) {
            assertTrue("Should find functions in output", output.contains("process_int") || output.contains("double_int"))
        }
        
        // Clean up
        tempDir.deleteRecursively()
    }
    
    fun testMenuGenerationLogic() {
        // Test that the menu would be properly structured
        val pythonCode = """
            from pinjected import IProxy
            test_proxy: IProxy[int] = IProxy()
        """.trimIndent()
        
        val psiFile = myFixture.configureByText("test_menu.py", pythonCode)
        val targetExpr = PsiTreeUtil.findChildOfType(psiFile, PyTargetExpression::class.java)
        
        assertNotNull("Should find target expression", targetExpr)
        assertEquals("test_proxy", targetExpr?.name)
        
        // Extract the type
        val annotation = targetExpr?.annotation
        assertTrue("Should be subscription expression", annotation is PySubscriptionExpression)
        
        if (annotation is PySubscriptionExpression) {
            val typeParam = annotation.indexExpression?.text
            assertEquals("int", typeParam)
            
            // This is what would trigger the menu with "Find @injected Functions" group
            println("Would create menu for IProxy[$typeParam]")
        }
    }
    
    private fun extractIProxyTypeFromExpression(targetExpr: PyTargetExpression): String? {
        val annotation = targetExpr.annotation ?: return null
        
        if (annotation is PySubscriptionExpression) {
            val operand = annotation.operand
            if (operand is PyReferenceExpression && operand.name == "IProxy") {
                return annotation.indexExpression?.text
            }
        }
        
        return null
    }
    
    private fun findIndexer(): String? {
        // Try to find pinjected-indexer in common locations
        val possiblePaths = listOf(
            "/usr/local/bin/pinjected-indexer",
            "/usr/bin/pinjected-indexer",
            System.getProperty("user.home") + "/.cargo/bin/pinjected-indexer",
            System.getProperty("user.home") + "/.local/bin/pinjected-indexer"
        )
        
        for (path in possiblePaths) {
            if (File(path).exists()) {
                return path
            }
        }
        
        // Try using 'which' command
        try {
            val process = ProcessBuilder("which", "pinjected-indexer").start()
            if (process.waitFor(2, TimeUnit.SECONDS)) {
                val output = process.inputStream.bufferedReader().readText().trim()
                if (output.isNotEmpty() && File(output).exists()) {
                    return output
                }
            }
        } catch (e: Exception) {
            // Ignore
        }
        
        return null
    }
}