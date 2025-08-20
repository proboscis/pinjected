package com.proboscis.pinjectdesign.kotlin.hints

import com.intellij.codeInsight.hints.*
import com.intellij.codeInsight.hints.presentation.*
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.util.PsiTreeUtil
import com.intellij.ui.dsl.builder.panel
import com.jetbrains.python.psi.*
import com.proboscis.pinjectdesign.kotlin.util.GutterActionUtilEnhanced
import javax.swing.JComponent
import com.intellij.icons.AllIcons

/**
 * Provides inline hints/buttons for IProxy[T] variables.
 * Shows a clickable button right after the variable name.
 */
@Suppress("UnstableApiUsage")
class IProxyInlayHintsProvider : InlayHintsProvider<IProxyInlayHintsProvider.Settings> {
    
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.hints.IProxyInlayHintsProvider")
    
    override val key: SettingsKey<Settings>
        get() = SettingsKey("pinjected.iproxy.hints")
    
    override val name: String
        get() = "IProxy Actions"
    
    override val previewText: String
        get() = """
            from pinjected import IProxy
            
            user_proxy: IProxy[User] = IProxy()  # [→] button appears here
            product_proxy: IProxy[Product] = IProxy()  # [→] button appears here
        """.trimIndent()
    
    override fun createSettings(): Settings = Settings()
    
    override fun getCollectorFor(
        file: PsiFile,
        editor: Editor,
        settings: Settings,
        sink: InlayHintsSink
    ): InlayHintsCollector? {
        if (file !is PyFile) {
            log.debug("Not a Python file, skipping inlay hints")
            return null
        }
        
        log.debug("Creating inlay hints collector for file: ${file.name}")
        
        return object : FactoryInlayHintsCollector(editor) {
            
            override fun collect(element: PsiElement, editor: Editor, sink: InlayHintsSink): Boolean {
                // Look for IProxy variable declarations
                if (element is PyTargetExpression) {
                    log.debug("Found PyTargetExpression: ${element.name}")
                    val annotation = element.annotation
                    
                    if (annotation != null) {
                        log.debug("Annotation found: ${annotation.text}")
                        if (isIProxyType(annotation)) {
                            val typeParam = extractTypeParameter(annotation)
                            if (typeParam != null) {
                                log.info("Adding inlay hint for IProxy[$typeParam] variable: ${element.name}")
                                
                                // Create the hint presentation
                                val presentation = createPresentation(
                                    element,
                                    typeParam,
                                    editor.project ?: return true
                                )
                                
                                // Add the hint after the variable name
                                val offset = element.textRange.endOffset
                                sink.addInlineElement(offset, false, presentation, false)
                            } else {
                                log.debug("No type parameter found for IProxy annotation")
                            }
                        } else {
                            log.debug("Annotation is not IProxy type")
                        }
                    } else {
                        // Check if the assigned value suggests it's an IProxy
                        val assignedValue = element.findAssignedValue()
                        if (assignedValue?.text?.contains("IProxy") == true) {
                            log.debug("Found IProxy in assigned value but no annotation: ${assignedValue.text}")
                        }
                    }
                }
                
                return true
            }
            
            private fun createPresentation(
                element: PyTargetExpression,
                typeParam: String,
                project: Project
            ): InlayPresentation {
                val factory = factory
                
                // Create base text: " [→]"
                var presentation = factory.text(" [")
                
                // Create clickable arrow icon
                val iconPresentation = factory.icon(AllIcons.Actions.Forward)
                
                // Make it clickable
                val clickableIcon = factory.onClick(iconPresentation, MouseButton.Left) { event, _ ->
                    log.debug("IProxy hint clicked for ${element.name}")
                    GutterActionUtilEnhanced.showHierarchicalPopup(
                        event,
                        project,
                        element.name ?: "unknown",
                        element.nameIdentifier
                    )
                }
                
                // Add hover effect
                val hoverIcon = factory.onHover(clickableIcon, object : InlayPresentationFactory.HoverListener {
                    override fun onHover(event: java.awt.event.MouseEvent, translated: java.awt.Point) {
                        // Optional: Change cursor or show tooltip
                    }
                    
                    override fun onHoverFinished() {
                        // Optional: Reset cursor
                    }
                })
                
                // Combine: " [" + icon
                presentation = factory.seq(presentation, hoverIcon)
                
                // Add closing bracket
                presentation = factory.seq(presentation, factory.text("]"))
                
                // Add tooltip
                presentation = factory.withTooltip(
                    "Click to see @injected functions for $typeParam",
                    presentation
                )
                
                // Return the final presentation
                return presentation
            }
            
            private fun isIProxyType(annotation: PsiElement): Boolean {
                log.debug("Checking if annotation is IProxy type: ${annotation.text}")
                
                // Handle PyAnnotationImpl wrapper (PyCharm PSI structure)
                val actualAnnotation = if (annotation is PyAnnotation) {
                    log.debug("Found PyAnnotation wrapper, extracting value...")
                    annotation.value
                } else {
                    annotation
                }
                
                // Handle IProxy[T] pattern
                if (actualAnnotation is PySubscriptionExpression) {
                    val operand = actualAnnotation.operand
                    log.debug("Subscription operand: ${operand?.text}")
                    if (operand is PyReferenceExpression) {
                        val isIProxy = operand.name == "IProxy"
                        log.debug("Is IProxy reference: $isIProxy (name=${operand.name})")
                        return isIProxy
                    }
                }
                
                // Handle simple IProxy without parameters
                if (actualAnnotation is PyReferenceExpression) {
                    val isIProxy = actualAnnotation.name == "IProxy"
                    log.debug("Is IProxy simple reference: $isIProxy")
                    return isIProxy
                }
                
                return false
            }
            
            private fun extractTypeParameter(annotation: PsiElement): String? {
                // Handle PyAnnotationImpl wrapper (PyCharm PSI structure)
                val actualAnnotation = if (annotation is PyAnnotation) {
                    log.debug("Found PyAnnotation wrapper in extractTypeParameter, extracting value...")
                    annotation.value
                } else {
                    annotation
                }
                
                if (actualAnnotation is PySubscriptionExpression) {
                    val typeParam = actualAnnotation.indexExpression?.text
                    log.debug("Extracted type parameter: $typeParam")
                    return typeParam
                }
                
                // For simple IProxy without parameters
                if (actualAnnotation is PyReferenceExpression && actualAnnotation.name == "IProxy") {
                    log.debug("Simple IProxy without type parameter, using 'Any'")
                    return "Any"
                }
                
                return null
            }
        }
    }
    
    override fun createConfigurable(settings: Settings): ImmediateConfigurable {
        return object : ImmediateConfigurable {
            override fun createComponent(listener: ChangeListener): JComponent {
                return panel {
                    row {
                        val checkbox = checkBox("Show inline buttons for IProxy variables")
                        checkbox.component.isSelected = settings.showInlineButtons
                        checkbox.component.addItemListener {
                            settings.showInlineButtons = checkbox.component.isSelected
                            listener.settingsChanged()
                        }
                    }
                    row {
                        val checkbox = checkBox("Show type parameter in hint")
                        checkbox.component.isSelected = settings.showTypeParameter
                        checkbox.component.addItemListener {
                            settings.showTypeParameter = checkbox.component.isSelected
                            listener.settingsChanged()
                        }
                    }
                }
            }
        }
    }
    
    data class Settings(
        var showInlineButtons: Boolean = true,
        var showTypeParameter: Boolean = false
    )
}