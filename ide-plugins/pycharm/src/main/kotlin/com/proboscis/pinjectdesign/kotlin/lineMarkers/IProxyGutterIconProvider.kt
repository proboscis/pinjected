package com.proboscis.pinjectdesign.kotlin.lineMarkers

import com.proboscis.pinjectdesign.kotlin.util.GutterActionUtilEnhanced
import com.intellij.codeInsight.daemon.GutterIconNavigationHandler
import com.intellij.codeInsight.daemon.LineMarkerInfo
import com.intellij.codeInsight.daemon.LineMarkerProvider
import com.intellij.icons.AllIcons
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.editor.markup.GutterIconRenderer
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.PySubscriptionExpression
import com.jetbrains.python.psi.PyReferenceExpression
import com.jetbrains.python.psi.PyClass
import com.jetbrains.python.psi.PyAnnotation
import java.awt.event.MouseEvent
import javax.swing.Icon

/**
 * Line marker provider that adds gutter icons for IProxy[T] variables.
 * These icons show available @injected functions that can work with the IProxy type.
 */
class IProxyGutterIconProvider : LineMarkerProvider {
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.lineMarkers.IProxyGutterIconProvider")
    
    override fun getLineMarkerInfo(element: PsiElement): LineMarkerInfo<*>? {
        // Only process name identifiers to avoid duplicate markers
        if (element.node?.elementType?.toString() != "Py:IDENTIFIER") {
            return null
        }
        
        // Check if this is a variable with IProxy[T] annotation
        val targetExpression = PsiTreeUtil.getParentOfType(element, PyTargetExpression::class.java)
        if (targetExpression == null) {
            return null
        }
        
        if (targetExpression.nameIdentifier != element) {
            return null
        }
        
        // Log that we found a potential target
        println("[IProxyGutterIcon] Found potential target: ${targetExpression.name}")
        println("[IProxyGutterIcon] Target text: ${targetExpression.text}")
        log.info("IProxyGutterIconProvider: Found potential target expression: ${targetExpression.name}")
        log.info("IProxyGutterIconProvider: Target text: ${targetExpression.text}")
        
        // Ignore elements inside classes
        if (PsiTreeUtil.getParentOfType(element, PyClass::class.java) != null) {
            println("[IProxyGutterIcon] Ignoring class member")
            log.debug("IProxyGutterIconProvider: Ignoring class member")
            return null
        }
        
        // Get the type annotation
        val annotation = targetExpression.annotation
        println("[IProxyGutterIcon] Annotation for ${targetExpression.name}: ${annotation?.text}")
        log.info("IProxyGutterIconProvider: Annotation for ${targetExpression.name}: ${annotation?.text}")
        
        if (annotation == null) {
            println("[IProxyGutterIcon] No annotation found for ${targetExpression.name}")
            log.debug("IProxyGutterIconProvider: No annotation found for ${targetExpression.name}")
            return null
        }
        
        // Check if it's an IProxy type
        val typeInfo = extractIProxyType(annotation)
        if (typeInfo == null) {
            return null
        }
        
        val (baseType, typeParam) = typeInfo
        if (baseType != "IProxy") {
            return null
        }
        
        log.info("=== IProxy Gutter Icon Detection ===")
        log.info("Found IProxy variable: ${targetExpression.name}")
        log.info("Type parameter: $typeParam")
        log.info("File: ${element.containingFile?.virtualFile?.path}")
        
        // Use a different icon to distinguish from the old provider
        val icon = AllIcons.Nodes.Plugin
        
        return createMarker(
            element,
            icon,
            "IProxy[$typeParam]: Find @injected functions",
            GutterIconRenderer.Alignment.LEFT,
            element.project,
            targetExpression.name ?: "unknown",
            typeParam
        )
    }
    
    /**
     * Extracts IProxy type information from a type annotation.
     * Returns pair of (base type, type parameter) or null if not an IProxy.
     */
    private fun extractIProxyType(annotation: PsiElement): Pair<String, String>? {
        // Handle PyAnnotationImpl wrapper (PyCharm PSI structure)
        val actualAnnotation = if (annotation is PyAnnotation) {
            println("[IProxyGutterIcon] Found PyAnnotation wrapper, extracting value...")
            val value = annotation.value
            println("[IProxyGutterIcon] Extracted value: ${value?.text}")
            value
        } else {
            annotation
        }
        
        // Handle IProxy[T] pattern
        if (actualAnnotation is PySubscriptionExpression) {
            val operand = actualAnnotation.operand
            if (operand is PyReferenceExpression && operand.name == "IProxy") {
                // Get the type parameter
                val indexExpression = actualAnnotation.indexExpression
                val typeParam = indexExpression?.text ?: return null
                println("[IProxyGutterIcon] Found IProxy[$typeParam]")
                return Pair("IProxy", typeParam)
            }
        }
        
        // Handle simple IProxy without parameters (rare)
        if (actualAnnotation is PyReferenceExpression && actualAnnotation.name == "IProxy") {
            println("[IProxyGutterIcon] Found simple IProxy without type parameter")
            return Pair("IProxy", "Any")
        }
        
        return null
    }
    
    private fun createMarker(
        element: PsiElement,
        icon: Icon,
        tooltip: String,
        alignment: GutterIconRenderer.Alignment,
        project: Project,
        variableName: String,
        typeParam: String
    ): LineMarkerInfo<PsiElement> {
        val range = element.textRange
        
        return LineMarkerInfo(
            element,
            range,
            icon,
            { tooltip },
            IProxyNavigationHandler(project, variableName, typeParam),
            alignment,
            { tooltip }
        )
    }
    
    /**
     * Navigation handler for IProxy gutter icons.
     */
    private class IProxyNavigationHandler(
        private val project: Project,
        private val variableName: String,
        private val typeParam: String
    ) : GutterIconNavigationHandler<PsiElement> {
        private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.lineMarkers.IProxyNavigationHandler")
        
        override fun navigate(e: MouseEvent?, element: PsiElement?) {
            if (element == null) {
                log.warn("Element is null, cannot navigate")
                return
            }
            
            log.debug("Navigating for IProxy variable: $variableName with type: $typeParam")
            
            // Save all modified documents
            FileDocumentManager.getInstance().saveAllDocuments()
            
            // Show hierarchical popup with grouped actions
            GutterActionUtilEnhanced.showHierarchicalPopup(e, project, variableName, element)
        }
    }
}