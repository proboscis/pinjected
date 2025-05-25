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
     * Simply displays raw configuration names from pinjected with only the 
     * Update Configurations as a static menu item.
     */
    fun createActions(project: Project, name: String): List<ActionItem> {
        // Save modified documents before running actions
        FileDocumentManager.getInstance().saveAllDocuments()
        
        val helper = InjectedFunctionActionHelper(project)
        val actions = mutableListOf<ActionItem>()
        
        // Update configuration cache action - ALWAYS AVAILABLE
        val updateConfigAction = ActionItem("Update Configurations") {
            helper.runInBackground("Updating configurations") { indicator ->
                helper.updateConfigurations()
            }
        }
        actions.add(updateConfigAction)
        
        // DYNAMICALLY ADD ALL ACTIONS FROM CONFIGURATIONS WITHOUT FILTERING
        try {
            val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: emptyList()
            
            // Add ALL configurations as actions without filtering
            for (config in configs) {
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
