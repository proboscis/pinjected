package com.proboscis.pinjectdesign.kotlin.error

import com.intellij.notification.Notification
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.notification.Notifications
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import java.io.StringWriter
import java.io.PrintWriter

/**
 * Centralized error handling for the Pinjected plugin.
 * Shows user-friendly error messages with actionable information.
 */
object ErrorHandler {
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.error.ErrorHandler")
    private const val NOTIFICATION_GROUP = "Pinjected Plugin"
    
    enum class ErrorType {
        PYTHON_NOT_FOUND,
        PINJECTED_NOT_INSTALLED,
        MODULE_NOT_FOUND,
        CONFIGURATION_EXTRACTION_FAILED,
        JSON_PARSING_FAILED,
        COMMAND_EXECUTION_FAILED,
        CACHE_ERROR,
        UNKNOWN
    }
    
    data class ErrorContext(
        val type: ErrorType,
        val message: String,
        val details: String? = null,
        val exception: Throwable? = null,
        val command: String? = null,
        val stdout: String? = null,
        val stderr: String? = null
    )
    
    fun handleError(project: Project?, context: ErrorContext) {
        log.error("Error occurred: ${context.type} - ${context.message}", context.exception)
        
        val (title, content, actions) = when (context.type) {
            ErrorType.PYTHON_NOT_FOUND -> Triple(
                "Python Interpreter Not Found",
                buildString {
                    appendLine("Unable to find Python interpreter.")
                    appendLine()
                    appendLine("**Current interpreter path:** ${context.details ?: "Not set"}")
                    appendLine()
                    appendLine("**How to fix:**")
                    appendLine("1. Go to File → Settings → Project → Python Interpreter")
                    appendLine("2. Select a valid Python interpreter with pinjected installed")
                    appendLine("3. Or install Python 3.8+ if not already installed")
                },
                listOf(
                    createAction("Open Settings") { e ->
                        openPythonInterpreterSettings(e.project)
                    }
                )
            )
            
            ErrorType.PINJECTED_NOT_INSTALLED -> Triple(
                "Pinjected Not Installed",
                buildString {
                    appendLine("The 'pinjected' package is not installed in your Python environment.")
                    appendLine()
                    appendLine("**Error details:**")
                    context.stderr?.let { appendLine(it.take(200)) }
                    appendLine()
                    appendLine("**How to fix:**")
                    appendLine("Run one of these commands in your terminal:")
                    appendLine("• `pip install pinjected`")
                    appendLine("• `uv add pinjected`")
                    appendLine("• `poetry add pinjected`")
                },
                listOf(
                    createAction("Copy pip command") { 
                        copyToClipboard("pip install pinjected")
                    },
                    createAction("Show Full Error") { 
                        showFullError(project, context)
                    }
                )
            )
            
            ErrorType.MODULE_NOT_FOUND -> Triple(
                "Module File Not Found",
                buildString {
                    appendLine("The specified Python module file does not exist.")
                    appendLine()
                    appendLine("**File path:** ${context.details ?: "Unknown"}")
                    appendLine()
                    appendLine("**Possible causes:**")
                    appendLine("• File was deleted or moved")
                    appendLine("• File path contains special characters")
                    appendLine("• Permission issues")
                },
                emptyList()
            )
            
            ErrorType.CONFIGURATION_EXTRACTION_FAILED -> Triple(
                "Failed to Extract Configurations",
                buildString {
                    appendLine("Unable to extract run configurations from the Python file.")
                    appendLine()
                    appendLine("**File:** ${context.details ?: "Unknown"}")
                    appendLine()
                    appendLine("**Common causes:**")
                    appendLine("• Syntax errors in the Python file")
                    appendLine("• Missing imports (pinjected not in PYTHONPATH)")
                    appendLine("• Circular imports in the module")
                    appendLine("• Invalid injected function definitions")
                    context.stderr?.let {
                        appendLine()
                        appendLine("**Error output:**")
                        appendLine(it.take(300))
                    }
                },
                listOf(
                    createAction("Run Diagnostics") { 
                        runDiagnostics(project)
                    },
                    createAction("Show Full Error") { 
                        showFullError(project, context)
                    }
                )
            )
            
            ErrorType.JSON_PARSING_FAILED -> Triple(
                "Failed to Parse Configuration Output",
                buildString {
                    appendLine("The plugin received invalid JSON from pinjected.")
                    appendLine()
                    appendLine("**This might indicate:**")
                    appendLine("• Version mismatch between plugin and pinjected")
                    appendLine("• Corrupted output from Python process")
                    appendLine("• Debug print statements in your code")
                    context.stdout?.let {
                        appendLine()
                        appendLine("**Received output (first 200 chars):**")
                        appendLine(it.take(200))
                    }
                },
                listOf(
                    createAction("Show Raw Output") { 
                        showRawOutput(project, context)
                    }
                )
            )
            
            ErrorType.COMMAND_EXECUTION_FAILED -> Triple(
                "Command Execution Failed",
                buildString {
                    appendLine("Failed to execute Python command.")
                    appendLine()
                    context.command?.let {
                        appendLine("**Command:** $it")
                    }
                    context.stderr?.let {
                        appendLine()
                        appendLine("**Error:**")
                        appendLine(it.take(300))
                    }
                },
                listOf(
                    createAction("Copy Command") { 
                        context.command?.let { copyToClipboard(it) }
                    },
                    createAction("Show Full Error") { 
                        showFullError(project, context)
                    }
                )
            )
            
            ErrorType.CACHE_ERROR -> Triple(
                "Configuration Cache Error",
                buildString {
                    appendLine("Failed to load or update configuration cache.")
                    appendLine()
                    appendLine("**Try:**")
                    appendLine("• Click 'Update Configurations' in the gutter menu")
                    appendLine("• Restart the IDE")
                    appendLine("• Check file permissions")
                },
                listOf(
                    createAction("Clear Cache") { 
                        clearCache(project)
                    }
                )
            )
            
            ErrorType.UNKNOWN -> Triple(
                "Unexpected Error",
                buildString {
                    appendLine(context.message)
                    context.exception?.let {
                        appendLine()
                        appendLine("**Error type:** ${it.javaClass.simpleName}")
                        appendLine("**Message:** ${it.message}")
                    }
                },
                listOf(
                    createAction("Show Details") { 
                        showFullError(project, context)
                    }
                )
            )
        }
        
        showErrorNotification(project, title, content, actions)
    }
    
    private fun showErrorNotification(
        project: Project?,
        title: String,
        content: String,
        actions: List<AnAction>
    ) {
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup(NOTIFICATION_GROUP)
            .createNotification(title, content, NotificationType.ERROR)
        
        actions.forEach { notification.addAction(it) }
        
        notification.notify(project)
    }
    
    private fun createAction(text: String, action: (AnActionEvent) -> Unit): AnAction {
        return object : AnAction(text) {
            override fun actionPerformed(e: AnActionEvent) {
                action(e)
            }
        }
    }
    
    private fun showFullError(project: Project?, context: ErrorContext) {
        val details = buildString {
            appendLine("Error Type: ${context.type}")
            appendLine("Message: ${context.message}")
            appendLine()
            
            context.command?.let {
                appendLine("Command: $it")
                appendLine()
            }
            
            context.stdout?.let {
                appendLine("Standard Output:")
                appendLine(it)
                appendLine()
            }
            
            context.stderr?.let {
                appendLine("Standard Error:")
                appendLine(it)
                appendLine()
            }
            
            context.exception?.let {
                appendLine("Exception Stack Trace:")
                val sw = StringWriter()
                it.printStackTrace(PrintWriter(sw))
                appendLine(sw.toString())
            }
        }
        
        Messages.showMessageDialog(
            project,
            details,
            "Pinjected Plugin Error Details",
            Messages.getErrorIcon()
        )
    }
    
    private fun showRawOutput(project: Project?, context: ErrorContext) {
        val output = context.stdout ?: "No output available"
        Messages.showMessageDialog(
            project,
            output,
            "Raw Python Output",
            Messages.getInformationIcon()
        )
    }
    
    private fun copyToClipboard(text: String) {
        val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
        val selection = java.awt.datatransfer.StringSelection(text)
        clipboard.setContents(selection, selection)
        
        showInfoNotification(null, "Copied to Clipboard", "Command copied: $text")
    }
    
    private fun openPythonInterpreterSettings(project: Project?) {
        // This would open the Python interpreter settings
        // Implementation depends on PyCharm API
        showInfoNotification(
            project, 
            "Open Settings", 
            "Please go to File → Settings → Project → Python Interpreter"
        )
    }
    
    private fun runDiagnostics(project: Project?) {
        // This would run diagnostic checks
        DiagnosticRunner.runDiagnostics(project)
    }
    
    private fun clearCache(project: Project?) {
        try {
            com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelperObject.cache.clear()
            showInfoNotification(project, "Cache Cleared", "Configuration cache has been cleared.")
        } catch (e: Exception) {
            handleError(project, ErrorContext(
                ErrorType.UNKNOWN,
                "Failed to clear cache",
                exception = e
            ))
        }
    }
    
    private fun showInfoNotification(project: Project?, title: String, content: String) {
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup(NOTIFICATION_GROUP)
            .createNotification(title, content, NotificationType.INFORMATION)
        
        notification.notify(project)
    }
    
    /**
     * Analyzes an exception and returns an appropriate ErrorContext
     */
    fun analyzeException(e: Exception, command: String? = null): ErrorContext {
        val message = e.message ?: "Unknown error"
        val stderr = extractStderr(message)
        
        return when {
            // Python interpreter issues
            message.contains("No such file or directory") && 
            (message.contains("python") || message.contains("python3")) -> {
                ErrorContext(
                    ErrorType.PYTHON_NOT_FOUND,
                    "Python interpreter not found",
                    details = command?.split(" ")?.firstOrNull(),
                    exception = e,
                    command = command
                )
            }
            
            message.contains("Cannot run program") && 
            (message.contains("python") || message.contains("python3")) -> {
                ErrorContext(
                    ErrorType.PYTHON_NOT_FOUND,
                    "Python interpreter not found",
                    details = command?.split(" ")?.firstOrNull(),
                    exception = e,
                    command = command
                )
            }
            
            // Pinjected not installed
            stderr.contains("No module named 'pinjected'") ||
            stderr.contains("ModuleNotFoundError: No module named 'pinjected'") ||
            stderr.contains("No module named pinjected") -> {
                ErrorContext(
                    ErrorType.PINJECTED_NOT_INSTALLED,
                    "Pinjected package is not installed",
                    exception = e,
                    command = command,
                    stderr = stderr
                )
            }
            
            // Import errors that might indicate configuration issues
            stderr.contains("ImportError") || stderr.contains("ModuleNotFoundError") -> {
                ErrorContext(
                    ErrorType.CONFIGURATION_EXTRACTION_FAILED,
                    "Failed to import required modules",
                    exception = e,
                    command = command,
                    stderr = stderr
                )
            }
            
            // File not found
            message.contains("No such file or directory") ||
            message.contains("does not exist") -> {
                ErrorContext(
                    ErrorType.MODULE_NOT_FOUND,
                    "File not found",
                    details = extractFilePath(message),
                    exception = e
                )
            }
            
            // JSON parsing errors
            message.contains("Failed to parse JSON") ||
            message.contains("JSONDecodeError") ||
            message.contains("Failed to find <pinjected> content") -> {
                ErrorContext(
                    ErrorType.JSON_PARSING_FAILED,
                    "Invalid JSON response from pinjected",
                    exception = e,
                    command = command
                )
            }
            
            // Command execution failures
            message.contains("Failed to run command") ||
            message.contains("Exit code:") && !message.contains("Exit code: 0") -> {
                ErrorContext(
                    ErrorType.COMMAND_EXECUTION_FAILED,
                    "Python command failed",
                    exception = e,
                    command = command,
                    stderr = stderr
                )
            }
            
            // Configuration extraction failures
            message.contains("Failed to find configurations") ||
            stderr.contains("Traceback") -> {
                ErrorContext(
                    ErrorType.CONFIGURATION_EXTRACTION_FAILED,
                    "Failed to extract configurations from Python file",
                    exception = e,
                    command = command,
                    stderr = stderr
                )
            }
            
            else -> {
                ErrorContext(
                    ErrorType.UNKNOWN,
                    message,
                    exception = e,
                    command = command,
                    stderr = if (stderr.isNotEmpty()) stderr else null
                )
            }
        }
    }
    
    private fun extractFilePath(message: String): String {
        // Extract file path from error message
        val match = Regex("'([^']+)'").find(message)
        return match?.groupValues?.get(1) ?: "Unknown"
    }
    
    private fun extractStderr(message: String): String {
        // Extract stderr from error message
        val parts = message.split("stderr=>")
        return if (parts.size > 1) parts[1].trim() else message
    }
}