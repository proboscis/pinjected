package com.proboscis.kotlinopenai

import com.intellij.lang.parameterInfo.*
import com.intellij.openapi.diagnostic.Logger
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyCallExpression
import com.jetbrains.python.psi.PyExpression
import com.jetbrains.python.psi.PyFunction
private val LOG = Logger.getInstance(InjectedFunctionParameterInfoHandler::class.java)

class InjectedFunctionParameterInfoHandler : ParameterInfoHandler<PyCallExpression, PyFunction> {
    // print hello in constructor:
    init {
        LOG.info("hello")
    }

    override fun findElementForParameterInfo(context: CreateParameterInfoContext): PyCallExpression? {
        // Find the PyCallExpression at the caret position
        println("looking for element for parameter info: ${context.file}")
        LOG.info("looking for element for parameter info: ${context.file}")
        throw RuntimeException("looking for element for parameter info: ${context.file}")
        val callExpression = ParameterInfoUtils.findParentOfType(context.file, context.offset, PyCallExpression::class.java)
        if (callExpression != null) {
            // Determine if this call expression refers to an @injected function
            val referencedFunction = callExpression.callee?.reference?.resolve() as? PyFunction
            if (referencedFunction != null && isInjectedFunction(referencedFunction)) {
                context.itemsToShow = arrayOf(referencedFunction)
                return callExpression
            }
        }
        return null
    }

    override fun findElementForUpdatingParameterInfo(context: UpdateParameterInfoContext): PyCallExpression? {
        // Find the PyCallExpression at the caret position
        val file = context.file
        val offset = context.offset
        val elementAt = file.findElementAt(offset)
        return PsiTreeUtil.getParentOfType(elementAt, PyCallExpression::class.java)
    }

    override fun showParameterInfo(element: PyCallExpression, context: CreateParameterInfoContext) {
        context.showHint(element, element.textOffset, this)
    }

    override fun updateParameterInfo(parameterOwner: PyCallExpression, context: UpdateParameterInfoContext) {
        val argumentList = parameterOwner.argumentList ?: return
        val offset = context.offset
        var currentParameterIndex = -1
        var currentOffset = 0

        for (expression in argumentList.arguments) {
            if (expression is PyExpression) {
                currentOffset = expression.textRange.startOffset
                if (offset >= currentOffset) {
                    currentParameterIndex++
                } else {
                    break
                }
            }
        }

        context.setCurrentParameter(currentParameterIndex)
    }

    override fun updateUI(p: PyFunction?, context: ParameterInfoUIContext) {
        println("updating parameter info")
        if (p != null) {
            val parametersAfterSlash = getParametersAfterSlash(p)
            val text = parametersAfterSlash.joinToString(", ")
            context.setupUIComponentPresentation(text, 0, text.length, false, false, false, context.defaultParameterColor)
        }
    }

    // Implement other required methods...
}