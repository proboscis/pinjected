package com.cyberagent.ailab.pinjectdesign.kotlin.actions

import com.cyberagent.ailab.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.cyberagent.ailab.pinjectdesign.kotlin.util.PinjectedConsoleUtil
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys

/**
 * Action to execute a test script in the console.
 * Based on the original TestExecuteScriptAction from the materials.
 */
class TestExecuteScriptAction : AnAction("Execute Test Script") {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val helper = InjectedFunctionActionHelper(project)
        val pinjectedUtil = PinjectedConsoleUtil(helper)
        val editor = e.getData(CommonDataKeys.EDITOR)
        
        try {
            val filePath = helper.getFilePath() ?: return
            pinjectedUtil.runInjected(filePath, "test", editor)
        } catch (ex: Exception) {
            helper.showNotification(
                "Error Executing Test Script",
                "Error: ${ex.message}",
                com.intellij.notification.NotificationType.ERROR
            )
        }
    }
}
