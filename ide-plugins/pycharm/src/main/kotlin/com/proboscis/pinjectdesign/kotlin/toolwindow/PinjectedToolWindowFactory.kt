package com.proboscis.pinjectdesign.kotlin.toolwindow

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.ContentFactory

/**
 * Factory for creating the Pinjected tool window.
 */
class PinjectedToolWindowFactory : ToolWindowFactory {
    
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val contentFactory = ContentFactory.getInstance()
        val panel = PinjectedToolWindowPanel(project)
        val content = contentFactory.createContent(panel, "", false)
        toolWindow.contentManager.addContent(content)
    }
    
    override fun isApplicable(project: Project): Boolean {
        // Only show for projects with Python SDK
        return true // We'll check Python availability in the panel itself
    }
}