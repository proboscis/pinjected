package com.proboscis.kotlinopenai
import com.intellij.codeInsight.completion.*
import com.intellij.patterns.PlatformPatterns
import com.jetbrains.python.PythonLanguage
import com.jetbrains.python.psi.PyFunction
import com.jetbrains.python.psi.PyParameterList
import com.intellij.psi.util.PsiTreeUtil
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.util.ProcessingContext
import com.jetbrains.python.psi.PyDecoratorList
import com.jetbrains.python.psi.PyParameter

fun isInjectedFunction(function: PyFunction): Boolean {
    val decorators: PyDecoratorList? = function.decoratorList
    return decorators?.decorators?.any { it.name == "injected" } ?: false
}

fun getParametersAfterSlash(function: PyFunction): List<PyParameter> {
    val text = function.text
    val parameterListText = text.substringAfter("(").substringBeforeLast(")").trim()
    val parameters = function.parameterList.parameters
    val parameterNames = parameterListText.split(",").map { it.trim().split(" ")[0] }

    val slashIndex = parameterNames.indexOfFirst { it == "/" }
    return if (slashIndex != -1) {
        val paramNamesAfterSlash = parameterNames.drop(slashIndex + 1)
        parameters.filter { paramNamesAfterSlash.contains(it.name) }
    } else {
        emptyList()
    }
}
class InjectedFunctionCompletionContributor : CompletionContributor() {
    init {
        extend(CompletionType.BASIC,
                PlatformPatterns.psiElement().withLanguage(PythonLanguage.INSTANCE),
                object : CompletionProvider<CompletionParameters>() {
                    override fun addCompletions(parameters: CompletionParameters,
                                                context: ProcessingContext,
                                                resultSet: CompletionResultSet) {
                        //println("parameters: $parameters")
                        val position = parameters.position
                        val function = PsiTreeUtil.getParentOfType(position, PyFunction::class.java)
                        if (function != null && isInjectedFunction(function)) {
                            val parametersAfterSlash = getParametersAfterSlash(function)
                            parametersAfterSlash.forEach { param ->
                                resultSet.addElement(LookupElementBuilder.create(param.name ?: ""))
                            }
                        }
                    }
                }
        )
    }
}
