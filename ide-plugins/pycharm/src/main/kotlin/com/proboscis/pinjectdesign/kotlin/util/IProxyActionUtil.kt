package com.proboscis.pinjectdesign.kotlin.util

import com.proboscis.pinjectdesign.kotlin.data.ActionItem
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.openapi.ui.popup.PopupChooserBuilder
import com.intellij.ui.awt.RelativePoint
import com.intellij.ui.components.JBList
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.awt.event.MouseEvent
import java.io.BufferedReader
import java.io.InputStreamReader
import javax.swing.DefaultListModel
import java.util.concurrent.CompletableFuture
import java.util.concurrent.TimeUnit

/**
 * Utility for handling IProxy[T] actions.
 * Integrates with pinjected-indexer to find matching @injected functions.
 */
object IProxyActionUtil {
    private val LOG = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.util.IProxyActionUtil")
    private val gson = Gson()
    
    data class InjectedFunction(
        val function_name: String,
        val module_path: String,
        val file_path: String,
        val line_number: Int,
        val parameter_name: String,
        val parameter_type: String,
        val docstring: String?
    )
    
    /**
     * Shows available @injected functions for an IProxy[T] variable.
     */
    fun showIProxyActions(
        project: Project,
        variableName: String,
        typeParam: String,
        mouseEvent: MouseEvent?
    ) {
        LOG.debug("Showing IProxy actions for variable: $variableName with type: $typeParam")
        
        // Query the indexer asynchronously
        queryInjectedFunctions(project, typeParam).thenAccept { functions ->
            ApplicationManager.getApplication().invokeLater {
                if (functions.isEmpty()) {
                    showNoFunctionsNotification(project, typeParam)
                } else {
                    showFunctionChooser(project, variableName, typeParam, functions, mouseEvent)
                }
            }
        }.exceptionally { error ->
            ApplicationManager.getApplication().invokeLater {
                showErrorNotification(project, error.message ?: "Unknown error")
            }
            null
        }
    }
    
    /**
     * Query pinjected-indexer for @injected functions matching the type.
     */
    internal fun queryInjectedFunctions(
        project: Project,
        typeParam: String
    ): CompletableFuture<List<InjectedFunction>> {
        return CompletableFuture.supplyAsync {
            try {
                val projectRoot = project.basePath ?: "."
                
                // Build the command
                val command = listOf(
                    "pinjected-indexer",
                    "--root", projectRoot,
                    "--log-level", "error",
                    "query-iproxy-functions",
                    typeParam
                )
                
                LOG.debug("Executing command: ${command.joinToString(" ")}")
                
                val processBuilder = ProcessBuilder(command)
                processBuilder.directory(java.io.File(projectRoot))
                
                val process = processBuilder.start()
                
                // Read the output
                val output = BufferedReader(InputStreamReader(process.inputStream))
                    .use { it.readText() }
                
                val exitCode = process.waitFor(5, TimeUnit.SECONDS)
                
                if (!exitCode) {
                    LOG.warn("Indexer process timed out")
                    return@supplyAsync emptyList<InjectedFunction>()
                }
                
                if (process.exitValue() != 0) {
                    val error = BufferedReader(InputStreamReader(process.errorStream))
                        .use { it.readText() }
                    LOG.warn("Indexer returned non-zero exit code: ${process.exitValue()}, error: $error")
                    return@supplyAsync emptyList<InjectedFunction>()
                }
                
                // Parse JSON output
                if (output.isBlank()) {
                    LOG.debug("No functions found for type: $typeParam")
                    return@supplyAsync emptyList<InjectedFunction>()
                }
                
                val listType = object : TypeToken<List<InjectedFunction>>() {}.type
                val functions: List<InjectedFunction> = gson.fromJson(output, listType)
                
                LOG.debug("Found ${functions.size} functions for type: $typeParam")
                functions
                
            } catch (e: Exception) {
                LOG.error("Error querying indexer", e)
                emptyList()
            }
        }
    }
    
    /**
     * Shows a popup chooser for selecting an @injected function.
     */
    private fun showFunctionChooser(
        project: Project,
        variableName: String,
        typeParam: String,
        functions: List<InjectedFunction>,
        mouseEvent: MouseEvent?
    ) {
        val listModel = DefaultListModel<String>()
        
        // Create display names for functions
        val displayNames = functions.map { func ->
            val moduleName = func.module_path.substringAfterLast('.')
            val docs = func.docstring?.let { " - ${it.take(50)}" } ?: ""
            "${func.function_name} (${moduleName})$docs"
        }
        
        displayNames.forEach { listModel.addElement(it) }
        
        val list = JBList(listModel)
        val builder = PopupChooserBuilder(list)
        
        builder.setTitle("Select @injected function for $typeParam")
        builder.setItemChoosenCallback {
            val index = list.selectedIndex
            if (index >= 0 && index < functions.size) {
                val selected = functions[index]
                executeInjectedFunction(project, variableName, selected)
            }
        }
        
        val popup = builder.createPopup()
        if (mouseEvent != null) {
            popup.show(RelativePoint(mouseEvent))
        } else {
            popup.showInFocusCenter()
        }
    }
    
    /**
     * Execute the selected @injected function with the IProxy variable.
     */
    private fun executeInjectedFunction(
        project: Project,
        variableName: String,
        function: InjectedFunction
    ) {
        LOG.debug("Executing function: ${function.function_name} with IProxy variable: $variableName")
        
        // Get the module path of the current file
        // In a real implementation, we'd get this from the PSI context
        val currentModule = "current_module"  // This should be derived from the current file
        
        // Build the pinjected call command
        val command = "pinjected call ${function.module_path} $currentModule.$variableName"
        
        // Show notification with the command
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup("Pinjected Plugin")
            .createNotification(
                "Execute @injected Function",
                """
                Function: ${function.function_name}
                Location: ${function.file_path}:${function.line_number}
                
                Command:
                $command
                
                Click here to copy the command to clipboard
                """.trimIndent(),
                NotificationType.INFORMATION
            )
        
        notification.addAction(object : com.intellij.openapi.actionSystem.AnAction("Copy Command") {
            override fun actionPerformed(e: com.intellij.openapi.actionSystem.AnActionEvent) {
                val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
                val selection = java.awt.datatransfer.StringSelection(command)
                clipboard.setContents(selection, selection)
                
                NotificationGroupManager.getInstance()
                    .getNotificationGroup("Pinjected Plugin")
                    .createNotification(
                        "Command Copied",
                        "The command has been copied to your clipboard",
                        NotificationType.INFORMATION
                    )
                    .notify(project)
            }
        })
        
        notification.notify(project)
    }
    
    /**
     * Shows notification when no functions are found.
     */
    private fun showNoFunctionsNotification(project: Project, typeParam: String) {
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup("Pinjected Plugin")
            .createNotification(
                "No @injected Functions Found",
                "No @injected functions found that accept type: $typeParam",
                NotificationType.INFORMATION
            )
        notification.notify(project)
    }
    
    /**
     * Shows error notification.
     */
    private fun showErrorNotification(project: Project, message: String) {
        val notification = NotificationGroupManager.getInstance()
            .getNotificationGroup("Pinjected Plugin")
            .createNotification(
                "Error Querying Functions",
                message,
                NotificationType.ERROR
            )
        notification.notify(project)
    }
}