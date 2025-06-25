package com.proboscis.pinjectdesign.kotlin.error

import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import java.io.File

/**
 * Runs diagnostic checks to help users troubleshoot plugin issues.
 */
object DiagnosticRunner {
    
    data class DiagnosticResult(
        val checkName: String,
        val passed: Boolean,
        val message: String,
        val details: String? = null
    )
    
    fun runDiagnostics(project: Project?) {
        ProgressManager.getInstance().run(object : Task.Backgroundable(
            project, 
            "Running Pinjected Plugin Diagnostics", 
            false
        ) {
            override fun run(indicator: ProgressIndicator) {
                val results = mutableListOf<DiagnosticResult>()
                
                indicator.text = "Checking Python interpreter..."
                indicator.fraction = 0.1
                results.add(checkPythonInterpreter(project))
                
                indicator.text = "Checking pinjected installation..."
                indicator.fraction = 0.3
                results.add(checkPinjectedInstallation(project))
                
                indicator.text = "Checking pinjected version..."
                indicator.fraction = 0.5
                results.add(checkPinjectedVersion(project))
                
                indicator.text = "Checking file access..."
                indicator.fraction = 0.7
                results.add(checkFileAccess(project))
                
                indicator.text = "Testing configuration extraction..."
                indicator.fraction = 0.9
                results.add(testConfigurationExtraction(project))
                
                indicator.fraction = 1.0
                
                showDiagnosticResults(project, results)
            }
        })
    }
    
    private fun checkPythonInterpreter(project: Project?): DiagnosticResult {
        return try {
            val helper = project?.let { InjectedFunctionActionHelper(it) }
            val interpreterPath = helper?.interpreterPath ?: "python3"
            
            if (!File(interpreterPath).exists() && !isInPath(interpreterPath)) {
                DiagnosticResult(
                    "Python Interpreter",
                    false,
                    "Python interpreter not found",
                    "Path: $interpreterPath"
                )
            } else {
                // Try to get Python version
                val versionOutput = helper?.runPython(listOf("--version"))?.trim() ?: "Unknown"
                DiagnosticResult(
                    "Python Interpreter",
                    true,
                    "Python found",
                    "Path: $interpreterPath\nVersion: $versionOutput"
                )
            }
        } catch (e: Exception) {
            DiagnosticResult(
                "Python Interpreter",
                false,
                "Failed to check Python",
                e.message
            )
        }
    }
    
    private fun checkPinjectedInstallation(project: Project?): DiagnosticResult {
        return try {
            val helper = project?.let { InjectedFunctionActionHelper(it) }
            
            // Try to import pinjected
            val output = helper?.runPython(listOf(
                "-c", 
                "import pinjected; print(f'Pinjected {pinjected.__version__} installed at {pinjected.__file__}')"
            ))?.trim()
            
            DiagnosticResult(
                "Pinjected Installation",
                true,
                "Pinjected is installed",
                output
            )
        } catch (e: Exception) {
            val errorMsg = e.message ?: ""
            if (errorMsg.contains("No module named 'pinjected'")) {
                DiagnosticResult(
                    "Pinjected Installation",
                    false,
                    "Pinjected is NOT installed",
                    "Install with: pip install pinjected"
                )
            } else {
                DiagnosticResult(
                    "Pinjected Installation",
                    false,
                    "Failed to check pinjected",
                    errorMsg
                )
            }
        }
    }
    
    private fun checkPinjectedVersion(project: Project?): DiagnosticResult {
        return try {
            val helper = project?.let { InjectedFunctionActionHelper(it) }
            
            // Check if meta_main exists (for compatibility)
            val metaMainCheck = helper?.runPython(listOf(
                "-c",
                """
                try:
                    import pinjected.meta_main
                    import pinjected.ide_supports.create_configs
                    print("meta_main: OK")
                    print("create_configs: OK")
                except ImportError as e:
                    print(f"Import error: {e}")
                """.trimIndent()
            ))?.trim()
            
            val hasMetaMain = metaMainCheck?.contains("meta_main: OK") == true
            val hasCreateConfigs = metaMainCheck?.contains("create_configs: OK") == true
            
            when {
                hasMetaMain && hasCreateConfigs -> DiagnosticResult(
                    "Pinjected Compatibility",
                    true,
                    "All required modules found",
                    metaMainCheck
                )
                !hasMetaMain -> DiagnosticResult(
                    "Pinjected Compatibility",
                    false,
                    "pinjected.meta_main not found",
                    "Your pinjected version may be too old. Update with: pip install --upgrade pinjected"
                )
                else -> DiagnosticResult(
                    "Pinjected Compatibility",
                    false,
                    "Some modules missing",
                    metaMainCheck
                )
            }
        } catch (e: Exception) {
            DiagnosticResult(
                "Pinjected Compatibility",
                false,
                "Failed to check compatibility",
                e.message
            )
        }
    }
    
    private fun checkFileAccess(project: Project?): DiagnosticResult {
        return try {
            val testFile = File.createTempFile("pinjected_test", ".py")
            testFile.writeText("# Test file")
            val canRead = testFile.canRead()
            val canWrite = testFile.canWrite()
            testFile.delete()
            
            if (canRead && canWrite) {
                DiagnosticResult(
                    "File Access",
                    true,
                    "File access OK",
                    "Can read and write temporary files"
                )
            } else {
                DiagnosticResult(
                    "File Access",
                    false,
                    "Limited file access",
                    "Read: $canRead, Write: $canWrite"
                )
            }
        } catch (e: Exception) {
            DiagnosticResult(
                "File Access",
                false,
                "File access check failed",
                e.message
            )
        }
    }
    
    private fun testConfigurationExtraction(project: Project?): DiagnosticResult {
        return try {
            val helper = project?.let { InjectedFunctionActionHelper(it) }
            
            // Create a minimal test file
            val testFile = File.createTempFile("pinjected_test", ".py")
            testFile.writeText("""
                from pinjected import injected
                
                @injected
                def test_func():
                    return "test"
            """.trimIndent())
            
            // Try to extract configurations
            val configs = helper?.findConfigurations(testFile.absolutePath)
            testFile.delete()
            
            if (configs != null && configs.isNotEmpty()) {
                DiagnosticResult(
                    "Configuration Extraction",
                    true,
                    "Can extract configurations",
                    "Found ${configs.size} configuration groups"
                )
            } else {
                DiagnosticResult(
                    "Configuration Extraction",
                    false,
                    "No configurations found",
                    "The extraction process completed but found no injected functions"
                )
            }
        } catch (e: Exception) {
            DiagnosticResult(
                "Configuration Extraction",
                false,
                "Configuration extraction failed",
                "${e.javaClass.simpleName}: ${e.message}"
            )
        }
    }
    
    private fun isInPath(command: String): Boolean {
        return try {
            val process = ProcessBuilder("which", command).start()
            process.waitFor() == 0
        } catch (e: Exception) {
            false
        }
    }
    
    private fun showDiagnosticResults(project: Project?, results: List<DiagnosticResult>) {
        val allPassed = results.all { it.passed }
        val title = if (allPassed) {
            "✓ All Diagnostics Passed"
        } else {
            "⚠ Diagnostic Issues Found"
        }
        
        val content = buildString {
            appendLine("**Pinjected Plugin Diagnostic Results**")
            appendLine()
            
            results.forEach { result ->
                val icon = if (result.passed) "✓" else "✗"
                appendLine("$icon **${result.checkName}**: ${result.message}")
                result.details?.let { 
                    appendLine("  $it")
                }
                appendLine()
            }
            
            if (!allPassed) {
                appendLine("**Next Steps:**")
                
                if (results.any { it.checkName == "Python Interpreter" && !it.passed }) {
                    appendLine("• Configure Python interpreter in Settings")
                }
                
                if (results.any { it.checkName == "Pinjected Installation" && !it.passed }) {
                    appendLine("• Install pinjected: `pip install pinjected`")
                }
                
                if (results.any { it.checkName == "Pinjected Compatibility" && !it.passed }) {
                    appendLine("• Update pinjected: `pip install --upgrade pinjected`")
                }
            }
        }
        
        val notificationType = if (allPassed) {
            NotificationType.INFORMATION
        } else {
            NotificationType.WARNING
        }
        
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup("Pinjected Plugin")
            .createNotification(title, content, notificationType)
        
        notification.notify(project)
    }
}