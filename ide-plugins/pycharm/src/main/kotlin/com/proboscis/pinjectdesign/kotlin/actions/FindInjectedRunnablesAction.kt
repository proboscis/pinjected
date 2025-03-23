package com.proboscis.pinjectdesign.kotlin.actions

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.notification.NotificationType

/**
 * Scans the current file for injected functions and adds run configurations for all of them.
 * Based on the original FindInjectedRunnablesAction from the materials.
 */
class FindInjectedRunnablesAction : AnAction("Find Injected Runnables") {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val helper = InjectedFunctionActionHelper(project)
        
        helper.runInBackground("Finding Injected Runnables") { indicator ->
            indicator.isIndeterminate = true
            val filePath = helper.getFilePath() ?: return@runInBackground
            
            try {
                val configs = helper.findConfigurations(filePath)
                val pyConfigs = configs.values.flatten()
                pyConfigs.forEach { c -> helper.addConfig(c) }
                
                helper.showNotification(
                    "Injected Functions Found",
                    "Found ${pyConfigs.size} injected functions in current file",
                    NotificationType.INFORMATION
                )
            } catch (e: Exception) {
                helper.showNotification(
                    "Error Finding Injected Functions",
                    "Error: ${e.message}",
                    NotificationType.ERROR
                )
            }
        }
    }
}
