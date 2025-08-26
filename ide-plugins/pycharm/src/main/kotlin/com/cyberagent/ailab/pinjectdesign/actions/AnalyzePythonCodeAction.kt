package com.cyberagent.ailab.pinjectdesign.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.ui.Messages

class AnalyzePythonCodeAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        Messages.showInfoMessage(
            "Python code analysis functionality will be implemented here.",
            "Analyze Python Code"
        )
    }
}
