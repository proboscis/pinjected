package com.proboscis.kotlinopenai

import com.intellij.codeInsight.navigation.actions.GotoDeclarationHandler
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiManager
import com.intellij.psi.search.GlobalSearchScope
import com.intellij.psi.util.QualifiedName
import com.jetbrains.python.psi.PyFile
import com.jetbrains.python.psi.PyFunction
import com.jetbrains.python.psi.PyNamedParameter
import com.jetbrains.python.psi.PyParameterList
import com.jetbrains.python.psi.stubs.PyModuleNameIndex

class InjectedGotoDeclarationHandler : GotoDeclarationHandler {

    var cache: BackgroundCache<Map<String, DesignMetadata>>? = null
    fun getCache(project: Project): BackgroundCache<Map<String, DesignMetadata>> =
            BackgroundCache<Map<String, DesignMetadata>>(project) { filename ->
                val helper = InjectedFunctionActionHelper(project)
                val meta = helper.designMetadata(helper.getFilePath()!!)
                val pairs = mapOf(*meta.map {
                    val key = it.key
                    //val value = it.location.toPsiElement(project)
                    key to it
                }.toTypedArray())
                pairs
            }

    override fun getGotoDeclarationTargets(
            sourceElement: PsiElement?,
            offset: Int,
            editor: Editor?
    ): Array<PsiElement>? {
        val tgt = findAncestorByType<PyNamedParameter>(sourceElement)
        // Check if source element is a positional-only named parameter inside a decorated function
//        println("tgt: $tgt")
//        println("tgt is PyNamedParameter: ${tgt is PyNamedParameter}")
//        println("tgt is PyNamedParameter and isPositionalContainer: ${(tgt is PyNamedParameter && tgt.isPositionalContainer)}")
//        println("tgt is PositionalOnlyParameter: ${isPositionalOnlyParameter(tgt)}")
        val function = findAncestorByType<PyFunction>(tgt) ?: return null
        val function_targets = listOf("injected", "injected_function")
        val instance_targets = listOf("injected_instance", "instance")
        if (cache == null) {
            cache = getCache(sourceElement?.project!!)
        }
        val meta = cache!!.getOrUpdate(function.containingFile.virtualFile.path)
        if (function_targets.any { name ->
                    function.decoratorList?.findDecorator(name) != null
                } && isPositionalOnlyParameter(tgt)
        ) {
            val elem = meta?.get(tgt?.name)?.location?.toPsiElement(sourceElement?.project!!)
            return arrayOf(elem ?: return null)
        }
        if (instance_targets.any { name ->
                    function.decoratorList?.findDecorator(name) != null
                } && !isPositionalOnlyParameter(tgt)) {
            val elem = meta?.get(tgt?.name)?.location?.toPsiElement(sourceElement?.project!!)
            return arrayOf(elem ?: return null)
        }
        return null
    }

    fun isPositionalOnlyParameter(element: PsiElement?): Boolean {
        if (element is PyNamedParameter) {
            // get parameter list and find the '/' separator to check if the parameter is positional-only
            val parameterList = findAncestorByType<PyParameterList>(element)
            println("parameterList: $parameterList")
            parameterList?.parameters?.find { it.text == "/" }?.let {
                return element.textOffset < it.textOffset
            }
            // if there is no '/' separator, then all parameters are not positional-only
        }
        return false
    }

    inline fun <reified T> findAncestorByType(element: PsiElement?): T? {
        var parent = element?.parent
        while (parent != null) {
            if (parent is T) {
                return parent
            }
            parent = parent.parent
        }
        return null
    }


    /**
     * つまり、残る問題は、Designのbindingから以下にジャンプ可能な情報を抜き出すかである。
     * 1. qualified name: (package.subpackage.module.variable)
     * 2. line number + offset => instancesへの直接代入など。
     * @injected については1,それ以外の直接適用については2を使う。
     */
}

object InjectedGotoDeclaration {
    fun resolveStringToPsiElement(project: Project, location: String): PsiElement? {
        /**
         * This function takes a string of the form "package.subpackage.module.variable" and returns the PsiElement
         */

        val parts = location.split('.')
        val variableName = parts.last()
        val packageName = parts.dropLast(1).joinToString(".")

        // Fetch the PyFile for the given package name
        val pyFiles = PyModuleNameIndex.findByQualifiedName(
                QualifiedName.fromDottedString(packageName),
                project,
                GlobalSearchScope.allScope(project))
        println("pyFiles: $pyFiles for location: $location")
        val targetFile = pyFiles.firstOrNull() as? PyFile ?: return null
        println("targetFile: $targetFile")

        // Return the target variable or function from the file
        return targetFile.findTopLevelAttribute(variableName) ?: targetFile.findTopLevelFunction(variableName)
    }

    fun navigateToFileOffset(project: Project, filePath: String, lineNumber: Int, charOffset: Int): PsiElement? {
        // Fetch the virtual file from the given path
        val virtualFile = LocalFileSystem.getInstance().findFileByPath(filePath) ?: return null
        val psiFile = PsiManager.getInstance(project).findFile(virtualFile) ?: return null

        // Get the document and compute the offset
        val document = PsiDocumentManager.getInstance(project).getDocument(psiFile) ?: return null
        val lineStartOffset = document.getLineStartOffset(lineNumber - 1) // -1 because line numbers are 0-based
        val targetOffset = lineStartOffset + charOffset

        // Fetch the PsiElement at the given offset
        return psiFile.findElementAt(targetOffset)
    }


}