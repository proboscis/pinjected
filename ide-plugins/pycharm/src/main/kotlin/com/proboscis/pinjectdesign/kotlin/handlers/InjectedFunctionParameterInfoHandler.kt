package com.proboscis.pinjectdesign.kotlin.handlers

import com.intellij.lang.parameterInfo.CreateParameterInfoContext
import com.intellij.lang.parameterInfo.ParameterInfoContext
import com.intellij.lang.parameterInfo.ParameterInfoHandler
import com.intellij.lang.parameterInfo.ParameterInfoUIContext
import com.intellij.lang.parameterInfo.UpdateParameterInfoContext
import com.intellij.psi.PsiElement
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.PyParameterInfoHandler
import com.jetbrains.python.psi.PyCallExpression
import com.jetbrains.python.psi.PyFunction
import com.jetbrains.python.psi.PyReferenceExpression

class InjectedFunctionParameterInfoHandler : ParameterInfoHandler<PyCallExpression, Array<String>> {
    
    override fun findElementForParameterInfo(context: CreateParameterInfoContext): PyCallExpression? {
        val element = context.file.findElementAt(context.offset) ?: return null
        val callExpression = PsiTreeUtil.getParentOfType(element, PyCallExpression::class.java) ?: return null
        
        // Check if this is an injected function call
        val callee = callExpression.callee
        if (callee is PyReferenceExpression) {
            val referencedElement = callee.reference.resolve()
            if (referencedElement is PyFunction && referencedElement.text.contains("@injected")) {
                // Get parameter names from the function
                val parameterNames = referencedElement.parameterList.parameters.map { it.name }.toTypedArray()
                context.itemsToShow = arrayOf(parameterNames)
                return callExpression
            }
        }
        
        return null
    }

    override fun findElementForUpdatingParameterInfo(context: UpdateParameterInfoContext): PyCallExpression? {
        val element = context.file.findElementAt(context.offset) ?: return null
        return PsiTreeUtil.getParentOfType(element, PyCallExpression::class.java)
    }

    override fun updateParameterInfo(parameterOwner: PyCallExpression, context: UpdateParameterInfoContext) {
        context.setCurrentParameter(getArgumentIndex(parameterOwner, context))
    }

    override fun updateUI(p: Array<String>, context: ParameterInfoUIContext) {
        if (p.isEmpty()) return
        
        val currentParameterIndex = context.currentParameterIndex
        val text = p.joinToString(", ")
        
        // Highlight the current parameter
        var highlightStartOffset = 0
        var highlightEndOffset = text.length
        
        if (currentParameterIndex >= 0 && currentParameterIndex < p.size) {
            var currentPos = 0
            for (i in 0 until p.size) {
                val paramLength = p[i].length
                if (i == currentParameterIndex) {
                    highlightStartOffset = currentPos
                    highlightEndOffset = currentPos + paramLength
                    break
                }
                // Add 2 for ", "
                currentPos += paramLength + (if (i < p.size - 1) 2 else 0)
            }
        }
        
        context.setupUIComponentPresentation(
            text,
            highlightStartOffset,
            highlightEndOffset,
            false,
            false,
            false,
            context.defaultParameterColor
        )
    }

    private fun getArgumentIndex(callExpression: PyCallExpression, context: ParameterInfoContext): Int {
        val offset = context.offset
        val arguments = callExpression.arguments
        
        for (i in arguments.indices) {
            val arg = arguments[i]
            if (arg.textRange.contains(offset)) {
                return i
            }
        }
        
        return -1
    }

    override fun showParameterInfo(element: PyCallExpression, context: CreateParameterInfoContext) {
        context.showHint(element, element.textRange.startOffset, this)
    }
}
