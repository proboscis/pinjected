package com.proboscis.pinjectdesign.kotlin.handlers

import com.intellij.codeInsight.navigation.actions.GotoDeclarationHandler
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.search.GlobalSearchScope
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.*
import com.jetbrains.python.psi.stubs.PyFunctionNameIndex

/**
 * Handler for navigating from dependency parameters in @injected/@instance functions
 * to the corresponding function definitions.
 * 
 * When clicking on a parameter name in an @injected or @instance function,
 * this handler searches for functions with the same name that are also decorated
 * with @injected or @instance, and allows navigation to them.
 */
class InjectedGotoDeclarationHandler : GotoDeclarationHandler {
    
    override fun getGotoDeclarationTargets(
        sourceElement: PsiElement?, 
        offset: Int, 
        editor: Editor?
    ): Array<PsiElement>? {
        if (sourceElement == null) return null
        
        val project = sourceElement.project
        
        // Check if we're clicking on a parameter name in an @injected/@instance function
        val parameterName = getParameterName(sourceElement) ?: return null
        val containingFunction = getContainingFunction(sourceElement) ?: return null
        
        // Verify the containing function has @injected or @instance decorator
        if (!hasInjectedOrInstanceDecorator(containingFunction)) {
            return null
        }
        
        // Search for matching functions
        val matchingFunctions = findMatchingInjectedFunctions(project, parameterName)
        
        return if (matchingFunctions.isNotEmpty()) {
            matchingFunctions.toTypedArray()
        } else {
            null
        }
    }
    
    /**
     * Gets the parameter name if the element is part of a function parameter.
     */
    private fun getParameterName(element: PsiElement): String? {
        // Handle different cases where user might click
        
        // Case 1: Clicking directly on the parameter name identifier
        val parentParameter = element.parent as? PyNamedParameter
        if (parentParameter != null) {
            return parentParameter.name
        }
        
        // Case 2: Clicking on parameter usage within function body
        if (element is PyTargetExpression || element.parent is PyTargetExpression) {
            val targetExpr = element as? PyTargetExpression ?: element.parent as PyTargetExpression
            
            // Check if this is a parameter of the containing function
            val function = PsiTreeUtil.getParentOfType(targetExpr, PyFunction::class.java)
            if (function != null) {
                val parameterNames = function.parameterList.parameters.mapNotNull { it.name }.toSet()
                val targetName = targetExpr.name
                if (targetName in parameterNames) {
                    return targetName
                }
            }
        }
        
        // Case 3: Clicking on reference to parameter in function body
        if (element is PyReferenceExpression || element.parent is PyReferenceExpression) {
            val refExpr = element as? PyReferenceExpression ?: element.parent as PyReferenceExpression
            
            // Check if this references a parameter
            val function = PsiTreeUtil.getParentOfType(refExpr, PyFunction::class.java)
            if (function != null) {
                val parameterNames = function.parameterList.parameters.mapNotNull { it.name }.toSet()
                val refName = refExpr.name
                if (refName in parameterNames) {
                    return refName
                }
            }
        }
        
        return null
    }
    
    /**
     * Gets the containing function of the element.
     */
    private fun getContainingFunction(element: PsiElement): PyFunction? {
        return PsiTreeUtil.getParentOfType(element, PyFunction::class.java)
    }
    
    /**
     * Checks if a function has @injected or @instance decorator.
     */
    private fun hasInjectedOrInstanceDecorator(function: PyFunction): Boolean {
        val decoratorList = function.decoratorList ?: return false
        
        return decoratorList.decorators.any { decorator ->
            when (val callee = decorator.callee) {
                is PyReferenceExpression -> {
                    val name = callee.name
                    name == "injected" || name == "instance"
                }
                is PyCallExpression -> {
                    // Handle cases like @injected() or @injected(protocol=...)
                    val calleeRef = callee.callee as? PyReferenceExpression
                    val name = calleeRef?.name
                    name == "injected" || name == "instance"
                }
                else -> false
            }
        }
    }
    
    /**
     * Finds all functions with the given name that have @injected or @instance decorator.
     */
    private fun findMatchingInjectedFunctions(project: Project, functionName: String): List<PsiElement> {
        val result = mutableListOf<PsiElement>()
        val scope = GlobalSearchScope.allScope(project)
        
        // Search for all functions with the given name using the index
        val functions = PyFunctionNameIndex.find(functionName, project, scope)
        
        // Filter to only include functions with @injected or @instance decorators
        for (function in functions) {
            if (hasInjectedOrInstanceDecorator(function)) {
                // Return the function name identifier for precise navigation
                function.nameIdentifier?.let { result.add(it) }
            }
        }
        
        return result
    }
}