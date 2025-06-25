package com.proboscis.pinjectdesign.kotlin.lineMarkers

import com.proboscis.pinjectdesign.kotlin.util.GutterActionUtil
import com.proboscis.pinjectdesign.kotlin.util.PinjectedDetectionUtil
import com.intellij.codeInsight.daemon.GutterIconNavigationHandler
import com.intellij.codeInsight.daemon.LineMarkerInfo
import com.intellij.codeInsight.daemon.LineMarkerProvider
import com.intellij.icons.AllIcons
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.editor.markup.GutterIconRenderer
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.psi.PsiElement
import java.awt.event.MouseEvent
import javax.swing.Icon

/**
 * Line marker provider that adds gutter icons for injected functions and variables.
 */
class InjectedFunctionGutterIconProvider : LineMarkerProvider {
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.lineMarkers.InjectedFunctionGutterIconProvider")
    
    override fun getLineMarkerInfo(element: PsiElement): LineMarkerInfo<*>? {
        // Only process name identifiers to avoid duplicate markers
        if (element.node?.elementType?.toString() != "Py:IDENTIFIER") {
            return null
        }
        
        val icon = AllIcons.Actions.Execute
        
        val targetName = PinjectedDetectionUtil.getInjectedTargetName(element)
        if (targetName != null) {
            log.debug("=== Gutter Icon Detection ===")
            log.debug("Found injected target: $targetName")
            log.debug("Element text: ${element.text}")
            log.debug("Element type: ${element.node?.elementType}")
            log.debug("Parent: ${element.parent?.javaClass?.simpleName}")
            log.debug("File: ${element.containingFile?.virtualFile?.path}")
            
            return createMarker(
                element,
                icon,
                "Run Injected: $targetName",
                GutterIconRenderer.Alignment.CENTER,
                element.project,
                targetName
            )
        }
        
        return null
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
        private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.lineMarkers.InjectedFunctionNavigationHandler")
        
        override fun navigate(e: MouseEvent?, element: PsiElement?) {
            if (element == null) {
                log.warn("Element is null, cannot navigate")
                return
            }
            
            log.debug("Navigating to injected target: $targetName")
            
            // Save all modified documents
            FileDocumentManager.getInstance().saveAllDocuments()
            
            // Show popup with actions
            val actions = GutterActionUtil.createActions(project, targetName)
            log.debug("Created ${actions.size} actions for $targetName")
            GutterActionUtil.showPopupChooser(e, actions)
        }
    }
}
