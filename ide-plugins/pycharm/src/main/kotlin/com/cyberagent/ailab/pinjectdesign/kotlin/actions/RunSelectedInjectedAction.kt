package com.cyberagent.ailab.pinjectdesign.kotlin.actions

import com.cyberagent.ailab.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.cyberagent.ailab.pinjectdesign.kotlin.util.PinjectedConsoleUtil
import com.intellij.notification.NotificationType
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.psi.PsiFile
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyAssignmentStatement
import com.jetbrains.python.psi.PyTargetExpression

fun saveModifiedDocuments() {
    val fileDocumentManager = FileDocumentManager.getInstance()
    fileDocumentManager.saveAllDocuments()
}

class RunSelectedInjectedAction : AnAction("Run Selected Injected") {
    override fun actionPerformed(e: AnActionEvent) {
        saveModifiedDocuments()
        val project = e.project ?: return
        val helper = InjectedFunctionActionHelper(project)
        val pinjectedUtil = PinjectedConsoleUtil(helper)
        val editor: Editor? = e.getData(CommonDataKeys.EDITOR)
        val file: PsiFile? = e.getData(CommonDataKeys.PSI_FILE)
        var found = false

        if (editor != null && file != null) {
            val offset = editor.caretModel.offset
            val elementAt = file.findElementAt(offset)
            val assignmentStatement = PsiTreeUtil.getParentOfType(elementAt, PyAssignmentStatement::class.java)
            assignmentStatement?.let { stmt ->
                val targets = stmt.targets
                if (targets.isNotEmpty()) {
                    val target = targets[0] as? PyTargetExpression
                    target?.let {
                        found = true
                        val variableName = it.name
                        val filePath = file.virtualFile.path
                        pinjectedUtil.runInjected(
                                filePath,
                                variableName!!,
                                editor
                        )
                    }
                }
            }
        }
        if (!found){
            helper.showNotification("No Injected Found", "No injected found at the current cursor position", NotificationType.INFORMATION)
        }
    }
}

class TestExecuteScriptAction : AnAction("Execute Test Script") {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val helper = InjectedFunctionActionHelper(project)
        val pinjectedUtil = PinjectedConsoleUtil(helper)
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        
        // Get the current file path
        val file = e.getData(CommonDataKeys.PSI_FILE) ?: return
        val filePath = file.virtualFile.path
        
        pinjectedUtil.runInjected(
                filePath,
                "run_test",
                editor
        )
    }
}
