package com.proboscis.pinjectdesign.config

import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.PyTypedElement
import kotlinx.serialization.Serializable

@Serializable
data class PyConfiguration(
        val name: String,
        val script_path: String,
        val interpreter_path: String,
        val arguments: List<String>,
        val working_dir: String
)

@Serializable
data class ConfigurationWrapper(val configs: Map<String, List<PyConfiguration>>)

fun saveModifiedDocuments() {
    val fileDocumentManager = FileDocumentManager.getInstance()
    fileDocumentManager.saveAllDocuments()
}

object InjectedFunctionActionHelperObject {
    val cache = mutableMapOf<String, Map<String, List<PyConfiguration>>>()
}

fun findTypeAnnotations(psiElement: PsiElement): List<PyTypedElement> {
    val typeAnnotations = mutableListOf<PyTypedElement>()
    PsiTreeUtil.processElements(psiElement, PyTargetExpression::class.java) { namedParameter ->
        if (namedParameter.annotation != null) {
            typeAnnotations.add(namedParameter)
        }
        true
    }
    return typeAnnotations
}
