package com.proboscis.pinjectdesign.kotlin.util

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.data.ActionItem
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.openapi.ui.popup.PopupChooserBuilder
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.ui.awt.RelativePoint
import com.intellij.ui.components.JBList
import java.awt.event.MouseEvent
import java.io.File
import javax.swing.DefaultListModel

/**
 * Utility class for handling gutter actions.
 */
object GutterActionUtil {
    private val LOG = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.util.GutterActionUtil")
    
    /**
     * Shows a popup chooser for selecting an action.
     */
    fun showPopupChooser(e: MouseEvent?, actionItems: List<ActionItem>) {
        LOG.debug("Showing popup chooser")
        val listModel = DefaultListModel<String>()
        actionItems.map { it.name }.forEach { listModel.addElement(it) }
        val list = JBList(listModel)
        val builder = PopupChooserBuilder(list)
        
        builder.setTitle("Choose an Action")
        builder.setItemChoosenCallback {
            val index = list.selectedIndex
            LOG.debug("Selected index: $index")
            val selectedItem = actionItems[index]
            LOG.debug("Selected item: ${selectedItem.name}")
            selectedItem.action()
        }
        
        val popup = builder.createPopup()
        if (e != null) {
            popup.show(RelativePoint(e))
        } else {
            popup.showInFocusCenter()
        }
    }
    
    /**
     * Creates a list of action items for an injected function/variable.
     * Follows the specific order: Run action (first), Show action (second), Describe action (third), Other actions (following)
     */
    fun createActions(project: Project, name: String): List<ActionItem> {
        // Save modified documents before running actions
        FileDocumentManager.getInstance().saveAllDocuments()
        
        val helper = InjectedFunctionActionHelper(project)
        val pinjectedUtil = PinjectedConsoleUtil(helper)
        val actions = mutableListOf<ActionItem>()
        
        // Basic run action - uses 'run' environment (default) - ALWAYS FIRST
        val runAction = ActionItem("Run $name") {
            helper.runInBackground("Running $name") { indicator ->
                try {
                    indicator.fraction = 0.1
                    val filePath = helper.getFilePath() ?: return@runInBackground
                    val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: return@runInBackground
                    val runConfig = configs.firstOrNull { !it.name.contains("_viz") && !it.name.contains("describe") }
                    
                    indicator.fraction = 0.5
                    if (runConfig != null) {
                        helper.runConfig(runConfig)
                    } else {
                        // Fallback to console if no run config found
                        pinjectedUtil.runInjected(filePath, name, null)
                    }
                    indicator.fraction = 1.0
                } catch (e: Exception) {
                    helper.showNotification(
                        "Error Running $name",
                        "Error: ${e.message}",
                        com.intellij.notification.NotificationType.ERROR
                    )
                }
            }
        }
        actions.add(runAction)
        
        // Show/Visualize action - ALWAYS SECOND
        val showAction = ActionItem("Show $name") {
            helper.runInBackground("Visualizing $name") { indicator ->
                indicator.fraction = 0.1
                val filePath = helper.getFilePath() ?: return@runInBackground
                
                try {
                    // Try to find a viz config or use standard config
                    val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: return@runInBackground
                    val vizConfig = configs.firstOrNull { it.name.endsWith("_viz") }
                    
                    indicator.fraction = 0.5
                    if (vizConfig != null) {
                        helper.runConfig(vizConfig)
                    } else {
                        // If no viz config, run standard
                        pinjectedUtil.runInjected(filePath, name, null)
                    }
                } catch (e: Exception) {
                    helper.showNotification(
                        "Error Visualizing $name",
                        "Error: ${e.message}",
                        com.intellij.notification.NotificationType.ERROR
                    )
                }
                
                indicator.fraction = 1.0
            }
        }
        actions.add(showAction)
        
        // Describe action - ALWAYS THIRD (if available)
        try {
            val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: emptyList()
            val describeConfig = configs.firstOrNull { it.name.contains("describe") }
            
            if (describeConfig != null) {
                val describeAction = ActionItem("Describe $name") {
                    helper.runInBackground("Describing $name") { indicator ->
                        indicator.fraction = 0.1
                        helper.runConfig(describeConfig)
                        indicator.fraction = 1.0
                    }
                }
                actions.add(describeAction)
            }
        } catch (e: Exception) {
            LOG.error("Error loading describe configuration for $name", e)
            helper.showNotification(
                "Error Loading Describe Configuration",
                "Error: ${e.message}",
                com.intellij.notification.NotificationType.ERROR
            )
        }
        
        // Update configuration cache action - ALWAYS AVAILABLE
        val updateConfigAction = ActionItem("Update Configurations") {
            helper.runInBackground("Updating configurations") { indicator ->
                helper.updateConfigurations()
            }
        }
        actions.add(updateConfigAction)
        
        // Make sandbox action
        val makeSandboxAction = ActionItem("Make Sandbox") {
            helper.runInBackground("Creating sandbox for $name") { indicator ->
                val filePath = helper.getFilePath() ?: return@runInBackground
                
                try {
                    // Create sandbox file
                    indicator.fraction = 0.3
                    val sandboxPath = helper.runPython(
                        listOf("-m", "pinjected.ide_supports.console_run_helper", "make-sandbox", filePath, name)
                    ).trim()
                    
                    // Open the sandbox file
                    indicator.fraction = 0.7
                    LocalFileSystem.getInstance().refreshIoFiles(listOf(File(sandboxPath)))
                    val virtualFile = LocalFileSystem.getInstance().findFileByIoFile(File(sandboxPath))
                        ?: throw Exception("Could not find sandbox file: $sandboxPath")
                            
                    ApplicationManager.getApplication().invokeLater {
                        FileEditorManager.getInstance(project).openFile(virtualFile, true)
                    }
                } catch (e: Exception) {
                    helper.showNotification(
                        "Error Creating Sandbox",
                        "Error: ${e.message}",
                        com.intellij.notification.NotificationType.ERROR
                    )
                }
                
                indicator.fraction = 1.0
            }
        }
        actions.add(makeSandboxAction)
        
        // DYNAMICALLY ADD OTHER ACTIONS FROM CONFIGURATIONS
        try {
            val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: emptyList()
            
            // Add all other configurations as actions
            for (config in configs) {
                // Skip configs we've already handled (run, viz, describe)
                if (!config.name.endsWith("_viz") && 
                    !config.name.contains("describe") && 
                    config.name != "Run $name") {
                    
                    val actionName = config.name
                    val action = ActionItem(actionName) {
                        helper.runInBackground("Running $actionName") { indicator ->
                            indicator.fraction = 0.1
                            helper.runConfig(config)
                            indicator.fraction = 1.0
                        }
                    }
                    actions.add(action)
                }
            }
        } catch (e: Exception) {
            LOG.error("Error loading configurations for $name", e)
            helper.showNotification(
                "Error Loading Configurations",
                "Error: ${e.message}",
                com.intellij.notification.NotificationType.ERROR
            )
        }
        
        return actions
    }
}
