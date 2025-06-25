package com.proboscis.pinjectdesign.kotlin.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.proboscis.pinjectdesign.kotlin.error.DiagnosticRunner

/**
 * Action to run diagnostics for the Pinjected plugin.
 * Helps users troubleshoot configuration issues.
 */
class RunDiagnosticsAction : AnAction("Run Pinjected Diagnostics") {
    
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project
        DiagnosticRunner.runDiagnostics(project)
    }
    
    override fun update(e: AnActionEvent) {
        // Always enable this action
        e.presentation.isEnabledAndVisible = true
        e.presentation.description = "Run diagnostics to check Pinjected plugin configuration"
    }
}