package com.proboscis.pinjectdesign.kotlin.util

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelperObject
import com.proboscis.pinjectdesign.kotlin.data.ActionItem
import com.proboscis.pinjectdesign.kotlin.error.DiagnosticRunner
import com.proboscis.pinjectdesign.kotlin.error.ErrorHandler
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
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
        LOG.debug("Showing popup chooser with ${actionItems.size} actions")
        actionItems.forEachIndexed { index, item ->
            LOG.debug("Action[$index]: ${item.name}")
        }
        
        val listModel = DefaultListModel<String>()
        actionItems.map { it.name }.forEach { listModel.addElement(it) }
        val list = JBList(listModel)
        val builder = PopupChooserBuilder(list)
        
        builder.setTitle("Choose an Action")
        builder.setItemChoosenCallback {
            val index = list.selectedIndex
            val selectedValue = list.selectedValue
            LOG.debug("Selected index: $index, selected value: $selectedValue")
            
            if (index >= 0 && index < actionItems.size) {
                val selectedItem = actionItems[index]
                LOG.debug("Executing action at index $index: ${selectedItem.name}")
                selectedItem.action()
            } else {
                LOG.error("Invalid index $index for actionItems of size ${actionItems.size}")
            }
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
     * Simply displays raw configuration names from pinjected with only the 
     * Update Configurations as a static menu item.
     * For IProxy variables, also shows available @injected functions.
     */
    fun createActions(project: Project, name: String): List<ActionItem> {
        LOG.debug("Creating actions for injected: $name")
        
        // Save modified documents before running actions
        FileDocumentManager.getInstance().saveAllDocuments()
        
        val helper = InjectedFunctionActionHelperObject.createSafely(project)
        val actions = mutableListOf<ActionItem>()
        
        // If no helper available (Python not configured), show diagnostic action
        if (helper == null) {
            actions.add(ActionItem("Configure Python Interpreter") {
                val notification = NotificationGroupManager.getInstance()
                    .getNotificationGroup("Pinjected Plugin")
                    .createNotification(
                        "Configure Python",
                        "Please configure a Python interpreter in Project Settings",
                        NotificationType.INFORMATION
                    )
                notification.notify(project)
            })
            actions.add(ActionItem("Run Diagnostics") {
                DiagnosticRunner.runDiagnostics(project)
            })
            return actions
        }
        
        // Update configuration cache action - ALWAYS AVAILABLE
        val updateConfigAction = ActionItem("Update Configurations") {
            helper.runInBackground("Updating configurations") { indicator ->
                helper.updateConfigurations()
            }
        }
        actions.add(updateConfigAction)
        LOG.debug("Added Update Configurations action at index 0")
        
        // DYNAMICALLY ADD ALL ACTIONS FROM CONFIGURATIONS WITHOUT FILTERING
        try {
            LOG.debug("Fetching configurations for key: '$name'")
            val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: emptyList()
            LOG.debug("Loaded ${configs.size} configurations for '$name'")
            
            if (configs.isEmpty()) {
                LOG.warn("No configurations found for '$name' - showing debug notification")
                
                // Get all available configurations to show what's actually available
                val filePath = helper.getFilePath()
                val allConfigs = if (filePath != null) {
                    InjectedFunctionActionHelperObject.cache[filePath] ?: emptyMap()
                } else {
                    emptyMap()
                }
                
                val availableKeys = allConfigs.keys.sorted()
                val totalConfigs = allConfigs.values.sumOf { it.size }
                
                // Create detailed debug message
                val message = buildString {
                    appendLine("Gutter Icon Configuration Mismatch!")
                    appendLine()
                    appendLine("Gutter icon clicked for: \"$name\"")
                    appendLine("File: ${filePath ?: "unknown"}")
                    appendLine()
                    appendLine("Total configurations in cache: $totalConfigs")
                    appendLine("Configuration groups found: ${availableKeys.size}")
                    appendLine()
                    appendLine("Available configuration keys:")
                    if (availableKeys.isEmpty()) {
                        appendLine("  (none - cache might be empty)")
                    } else {
                        availableKeys.forEach { key ->
                            val count = allConfigs[key]?.size ?: 0
                            appendLine("  • $key ($count configs)")
                        }
                    }
                    appendLine()
                    appendLine("Possible causes:")
                    appendLine("• Function/variable name doesn't match configuration key")
                    appendLine("• Configuration extraction failed")
                    appendLine("• Cache needs updating (try 'Update Configurations')")
                }
                
                val notification = NotificationGroupManager.getInstance()
                    .getNotificationGroup("Pinjected Plugin")
                    .createNotification(
                        "Configuration Not Found for Gutter Icon",
                        message,
                        NotificationType.WARNING
                    )
                notification.notify(project)
            }
            
            // Check for duplicate names
            val configNames = configs.map { it.name }
            val duplicateNames = configNames.groupBy { it }.filter { it.value.size > 1 }.keys
            if (duplicateNames.isNotEmpty()) {
                LOG.warn("Found duplicate configuration names: $duplicateNames")
            }
            
            // Add ALL configurations as actions without filtering
            configs.forEachIndexed { configIndex, config ->
                // Make action names unique by adding index if there are duplicates
                val actionName = if (configNames.count { it == config.name } > 1) {
                    "${config.name} [${configIndex + 1}]"
                } else {
                    config.name
                }
                LOG.debug("Adding configuration[$configIndex]: $actionName (script: ${config.script_path})")
                
                // Capture the config in a local variable to ensure correct closure
                val capturedConfig = config
                val action = ActionItem(actionName) {
                    LOG.debug("Executing action: $actionName for config: ${capturedConfig.script_path} with args: ${capturedConfig.arguments}")
                    helper.runInBackground("Running $actionName") { indicator ->
                        indicator.fraction = 0.1
                        helper.runConfig(capturedConfig)
                        indicator.fraction = 1.0
                    }
                }
                actions.add(action)
                LOG.debug("Added action '${actionName}' at index ${actions.size - 1}")
            }
        } catch (e: Exception) {
            LOG.error("Error loading configurations for $name", e)
            
            // The error is already shown by cachedConfigurations or findConfigurations
            // Just add a fallback action for users to diagnose the issue
            actions.add(ActionItem("Run Diagnostics") {
                com.proboscis.pinjectdesign.kotlin.error.DiagnosticRunner.runDiagnostics(project)
            })
        }
        
        LOG.debug("Total actions created: ${actions.size}")
        return actions
    }
}
