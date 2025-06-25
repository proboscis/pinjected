package com.proboscis.pinjectdesign.kotlin.actions

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.util.GutterActionUtil
import com.proboscis.pinjectdesign.kotlin.util.PinjectedDetectionUtil
import com.intellij.notification.NotificationType
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project

fun saveModifiedDocuments() {
    val fileDocumentManager = FileDocumentManager.getInstance()
    fileDocumentManager.saveAllDocuments()
}

open class RunSelectedInjectedAction : AnAction("Run Selected Injected") {
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.actions.RunSelectedInjectedAction")
    
    override fun actionPerformed(e: AnActionEvent) {
        saveModifiedDocuments()
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR)
        val file = e.getData(CommonDataKeys.PSI_FILE)

        if (editor != null && file != null) {
            val offset = editor.caretModel.offset
            val elementAt = file.findElementAt(offset)
            
            if (elementAt != null) {
                // Use the same detection logic as the gutter icon
                val targetName = PinjectedDetectionUtil.getInjectedTargetName(elementAt)
                
                if (targetName != null) {
                    log.debug("Found injected target: $targetName")
                    
                    // Show the same popup menu as the gutter icon
                    val actions = GutterActionUtil.createActions(project, targetName)
                    log.debug("Created ${actions.size} actions for $targetName")
                    GutterActionUtil.showPopupChooser(e.inputEvent as? java.awt.event.MouseEvent, actions)
                } else {
                    showNotification(
                        project,
                        "No Injected Found", 
                        "No injected function or variable found at the current cursor position", 
                        NotificationType.INFORMATION
                    )
                }
            }
        } else {
            showNotification(
                project,
                "Invalid Context", 
                "Unable to determine context from editor", 
                NotificationType.WARNING
            )
        }
    }
    
    private fun showNotification(project: Project?, title: String, content: String, type: NotificationType) {
        val notification = com.intellij.notification.NotificationGroupManager.getInstance()
            .getNotificationGroup("Pinjected Plugin")
            .createNotification(title, content, type)
        notification.notify(project)
    }
    
    // Factory methods for testing
    open fun createHelper(project: com.intellij.openapi.project.Project): InjectedFunctionActionHelper {
        return InjectedFunctionActionHelper(project)
    }
}
