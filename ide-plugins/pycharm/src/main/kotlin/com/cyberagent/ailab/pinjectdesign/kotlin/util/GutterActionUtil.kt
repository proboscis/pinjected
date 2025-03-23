package com.cyberagent.ailab.pinjectdesign.kotlin.util

import com.cyberagent.ailab.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.cyberagent.ailab.pinjectdesign.kotlin.data.ActionItem
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.openapi.ui.popup.PopupChooserBuilder
import com.intellij.ui.awt.RelativePoint
import com.intellij.ui.components.JBList
import java.awt.event.MouseEvent
import javax.swing.DefaultListModel

/**
 * Utility class for handling gutter actions.
 */
object GutterActionUtil {
    private val LOG = Logger.getInstance("com.cyberagent.ailab.pinjectdesign.kotlin.util.GutterActionUtil")
    
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
     */
    fun createActions(project: Project, name: String): List<ActionItem> {
        // Save modified documents before running actions
        FileDocumentManager.getInstance().saveAllDocuments()
        
        val helper = InjectedFunctionActionHelper(project)
        val pinjectedUtil = PinjectedConsoleUtil(helper)
        
        // Basic actions
        val runAction = ActionItem("Run $name") {
            helper.runInBackground("Running $name") { indicator ->
                val filePath = helper.getFilePath() ?: return@runInBackground
                pinjectedUtil.runInjected(filePath, name, null)
            }
        }
        
        val updateConfigAction = ActionItem("Update Configuration") {
            helper.runInBackground("Updating configurations") { indicator ->
                helper.updateConfigurations()
            }
        }
        
        return listOf(runAction, updateConfigAction)
    }
}
