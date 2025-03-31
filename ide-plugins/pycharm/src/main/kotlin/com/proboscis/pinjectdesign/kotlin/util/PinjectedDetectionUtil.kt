package com.proboscis.pinjectdesign.kotlin.util

import com.intellij.psi.PsiElement
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyClass
import com.jetbrains.python.psi.PyExpression
import com.jetbrains.python.psi.PyFunction
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.types.PyType
import com.jetbrains.python.psi.types.TypeEvalContext

/**
 * Utility class for detecting Pinjected-related elements in Python code.
 */
object PinjectedDetectionUtil {
    private val INJECTED_FUNCTION_MARKERS = listOf(
        "@Injected.bind", "provide_", 
        "@injected_instance", "@injected", "@instance"
    )
    
    private val INJECTED_TYPE_MARKERS = listOf(
        "Injected", "DelegatedVar", "PartialInjectedFunction", "Designed"
    )
    
    /**
     * Gets the inferred type of a PSI element.
     */
    fun getInferredType(element: PsiElement): String? {
        // Get the PyExpression from the PsiElement
        val pyExpression = PsiTreeUtil.getParentOfType(element, PyExpression::class.java) ?: return null
        
        // Get the TypeEvalContext for the element
        val typeEvalContext = TypeEvalContext.userInitiated(element.project, element.containingFile)
        
        // Get the inferred type
        val inferredType: PyType? = typeEvalContext.getType(pyExpression)
        
        // Return the type as a String, or null if the type could not be inferred
        return inferredType?.name
    }
    
    /**
     * Gets the name of an injected target if the element is part of an injected variable/function.
     * Returns null if the element is not part of an injected variable/function.
     */
    fun getInjectedTargetName(element: PsiElement): String? {
        // Ignore elements inside classes
        if (PsiTreeUtil.getParentOfType(element, PyClass::class.java) != null) {
            return null
        }
        
        // Check if it's an injected variable
        val pyVarDef = PsiTreeUtil.getParentOfType(element, PyTargetExpression::class.java)
        val typeName = getInferredType(element)
        
        pyVarDef?.let {
            if (INJECTED_TYPE_MARKERS.any { marker -> typeName?.contains(marker) == true }) {
                return pyVarDef.name
            }
        }
        
        // Check if it's an injected function
        val pyFunction = PsiTreeUtil.getParentOfType(element, PyFunction::class.java) ?: return null
        
        // If the PyTargetExpression also has the same PyFunction ancestor, it means it's in the function body.
        if (pyVarDef != null && PsiTreeUtil.getParentOfType(pyVarDef, PyFunction::class.java) == pyFunction) {
            return null
        }
        
        // Check if the function has any injected markers
        val containsMarker = INJECTED_FUNCTION_MARKERS.any { pyFunction.text.contains(it) }
        if (pyFunction.nameIdentifier == element && containsMarker) {
            return pyFunction.name
        }
        
        return null
    }
}
