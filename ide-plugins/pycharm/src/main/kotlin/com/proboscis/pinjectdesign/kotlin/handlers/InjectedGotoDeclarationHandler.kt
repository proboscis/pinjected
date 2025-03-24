package com.proboscis.pinjectdesign.kotlin.handlers

import com.intellij.codeInsight.navigation.actions.GotoDeclarationHandler
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiManager
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyReferenceExpression
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.data.BindingLocation
import com.proboscis.pinjectdesign.kotlin.data.DesignMetadata
import java.io.File

class InjectedGotoDeclarationHandler : GotoDeclarationHandler {
    
    override fun getGotoDeclarationTargets(sourceElement: PsiElement?, offset: Int, editor: Editor?): Array<PsiElement>? {
        if (sourceElement == null || editor == null) return null
        
        val project = sourceElement.project
        val referenceExpression = PsiTreeUtil.getParentOfType(sourceElement, PyReferenceExpression::class.java) ?: return null
        
        // Check if this is an injected reference
        val referenceName = referenceExpression.name ?: return null
        
        // Get the current file path
        val file = sourceElement.containingFile
        val filePath = file.virtualFile?.path ?: return null
        
        // Get design metadata for the file
        val helper = InjectedFunctionActionHelper(project)
        try {
            val metadata = helper.designMetadata(filePath)
            
            // Find matching binding
            val matchingBinding = metadata.find { it.key == referenceName }
            if (matchingBinding != null) {
                return resolveBindingLocation(project, matchingBinding.location)
            }
        } catch (e: Exception) {
            helper.showNotification("Error", "Failed to resolve declaration: ${e.message}")
        }
        
        return null
    }
    
    private fun resolveBindingLocation(project: Project, location: BindingLocation): Array<PsiElement>? {
        return when (location.type) {
            "path" -> {
                val element = resolveStringToPsiElement(project, location.value)
                if (element != null) arrayOf(element) else null
            }
            "coordinates" -> {
                val parts = location.value.split(":")
                if (parts.size >= 3) {
                    val filePath = parts[0]
                    val lineNo = parts[1].toIntOrNull() ?: return null
                    val colNo = parts[2].toIntOrNull() ?: return null
                    
                    val element = navigateToFileOffset(project, filePath, lineNo, colNo)
                    if (element != null) arrayOf(element) else null
                }
                else null
            }
            else -> null
        }
    }
    
    companion object {
        fun resolveStringToPsiElement(project: Project, path: String): PsiElement? {
            val file = File(path)
            if (!file.exists()) return null
            
            val virtualFile = LocalFileSystem.getInstance().findFileByIoFile(file) ?: return null
            return PsiManager.getInstance(project).findFile(virtualFile)
        }
        
        fun navigateToFileOffset(project: Project, filePath: String, lineNo: Int, colNo: Int): PsiElement? {
            val file = File(filePath)
            if (!file.exists()) return null
            
            val virtualFile = LocalFileSystem.getInstance().findFileByIoFile(file) ?: return null
            val psiFile = PsiManager.getInstance(project).findFile(virtualFile) ?: return null
            
            // Convert line and column to offset
            val document = psiFile.viewProvider.document ?: return null
            val offset = try {
                document.getLineStartOffset(lineNo - 1) + colNo - 1
            } catch (e: Exception) {
                return null
            }
            
            return psiFile.findElementAt(offset)
        }
    }
}
