package com.cyberagent.ailab.pinjectdesign.kotlin.lineMarkers

import com.cyberagent.ailab.pinjectdesign.kotlin.util.GutterActionUtil
import com.cyberagent.ailab.pinjectdesign.kotlin.util.PinjectedDetectionUtil
import com.intellij.codeInsight.daemon.GutterIconNavigationHandler
import com.intellij.codeInsight.daemon.LineMarkerInfo
import com.intellij.codeInsight.daemon.LineMarkerProvider
import com.intellij.icons.AllIcons
import com.intellij.openapi.editor.markup.GutterIconRenderer
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.psi.PsiElement
import java.awt.event.MouseEvent
import javax.swing.Icon

/**
 * Line marker provider that adds gutter icons for injected functions and variables.
 */
class InjectedFunctionGutterIconProvider : LineMarkerProvider {
    
    override fun getLineMarkerInfo(element: PsiElement): LineMarkerInfo<*>? {
        val icon = AllIcons.Actions.Execute
        
        return PinjectedDetectionUtil.getInjectedTargetName(element)?.let { targetName ->
            createMarker(
                element,
                icon,
                "Run Injected: $targetName",
                GutterIconRenderer.Alignment.CENTER,
                element.project,
                targetName
            )
        }
    }
    
    private fun createMarker(
        element: PsiElement,
        icon: Icon,
        tooltip: String,
        alignment: GutterIconRenderer.Alignment,
        project: com.intellij.openapi.project.Project,
        targetName: String
    ): LineMarkerInfo<PsiElement> {
        val range = element.textRange
        
        return LineMarkerInfo(
            element,
            range,
            icon,
            { tooltip },
            InjectedFunctionNavigationHandler(project, targetName),
            alignment,
            { tooltip }
        )
    }
    
    /**
     * Navigation handler for injected function gutter icons.
     */
    private class InjectedFunctionNavigationHandler(
        private val project: com.intellij.openapi.project.Project,
        private val targetName: String
    ) : GutterIconNavigationHandler<PsiElement> {
        
        override fun navigate(e: MouseEvent?, element: PsiElement?) {
            if (element == null) return
            
            // Save all modified documents
            FileDocumentManager.getInstance().saveAllDocuments()
            
            // Show popup with actions
            val actions = GutterActionUtil.createActions(project, targetName)
            GutterActionUtil.showPopupChooser(e, actions)
        }
    }
}
