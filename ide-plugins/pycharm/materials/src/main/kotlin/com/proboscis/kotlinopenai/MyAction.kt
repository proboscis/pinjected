package com.proboscis.kotlinopenai

import com.intellij.diff.DiffContentFactory
import com.intellij.diff.DiffManager
import com.intellij.diff.requests.SimpleDiffRequest
import com.intellij.diff.util.DiffUserDataKeys
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.PlatformDataKeys
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.EditorFactory
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.intellij.openapi.fileTypes.FileTypeManager
import com.intellij.openapi.fileTypes.PlainTextFileType
import com.intellij.openapi.ui.Messages
import com.proboscis.kotlinopenai.chatgpt.Bots
import com.proboscis.kotlinopenai.chatgpt.Conversation
import kotlin.reflect.KFunction1


data class ReplaceContext(
        val editor: Editor,
        val selection: String
)

open class ReplaceAction(val impl: KFunction1<ReplaceContext, String?>) : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project
        val editor = e.dataContext.getData(PlatformDataKeys.EDITOR)

        editor?.let { // Shorten null check
            val text = editor.selectionModel.selectedText
            // I want to get the surrounding text..

            text?.let { // Shorten null check
                WriteCommandAction.runWriteCommandAction(project) {
                    val cxt = ReplaceContext(editor, text)
                    cxt.let(impl)?.let {
                        editor.replaceSelectedText(it) // Utilize extension function
                    }
                }
            }
        }
    }
}

class DocumentModListener(val editor: Editor) : DocumentListener {
    override fun documentChanged(e: DocumentEvent) {
        editor.replaceSelectedText(e.document.text)
    }
}

open class ReplaceWithDiffAction(val impl: (ReplaceContext) -> String?) : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(PlatformDataKeys.EDITOR) ?: return
        val selectedText = editor.selectionModel.selectedText ?: return

        impl(ReplaceContext(editor, selectedText))?.let { generatedText ->
            val diffContentFactory = DiffContentFactory.getInstance()
            val originalDocument = EditorFactory.getInstance().createDocument(selectedText)
            originalDocument.addDocumentListener(DocumentModListener(editor))

            val fileType = e.getData(PlatformDataKeys.VIRTUAL_FILE)?.let {
                FileTypeManager.getInstance().getFileTypeByFile(it)
            } ?: PlainTextFileType.INSTANCE
            val originalContent = diffContentFactory.create(project, originalDocument, fileType)
            val generatedContent = diffContentFactory.create(project, generatedText, fileType)

            DiffManager.getInstance().showDiff(
                    project,
                    SimpleDiffRequest("Code Difference", originalContent, generatedContent, "Original", "Generated")
                            .apply { putUserData(DiffUserDataKeys.MERGE_EDITOR_FLAG, true) }
            )
        }
    }
}

data class InstructedReplaceContext(
        val editor: Editor,
        val selection: String,
        val instruction: String
)

open class InstructedReplaceWithDiffAction(val impl: (InstructedReplaceContext) -> String?) : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        // Get project, editor and selected text from event
        val project = e.project ?: return
        val editor = e.getData(PlatformDataKeys.EDITOR) ?: return
        val selectedText = editor.selectionModel.selectedText ?: return

        // Show input dialog to get instruction
        val instruction = showInputDialog("Please enter your instruction") ?: return

        // Call implementation function with context
        // let's do this in background
        val helper = InjectedFunctionActionHelper(project)
        helper.runInBackground("Generating Text with GPT..."){
            indicator->
            impl(InstructedReplaceContext(editor, selectedText, instruction))?.let { generatedText ->
                // Create diff content factory
                ApplicationManager.getApplication().invokeLater{
                    val diffContentFactory = DiffContentFactory.getInstance()

                    // Create original document
                    val originalDocument = EditorFactory.getInstance().createDocument(selectedText)
                    originalDocument.addDocumentListener(DocumentModListener(editor))

                    // Get file type from virtual file
                    val fileType = e.getData(PlatformDataKeys.VIRTUAL_FILE)?.let {
                        FileTypeManager.getInstance().getFileTypeByFile(it)
                    } ?: PlainTextFileType.INSTANCE

                    // Create original and generated content
                    val originalContent = diffContentFactory.create(project,editor.document)
                    val generatedContent = diffContentFactory.create(project, generatedText, fileType)

                    // Show diff
                    DiffManager.getInstance().showDiff(
                        project,
                        SimpleDiffRequest("Code Difference", originalContent, generatedContent, "Original", "Generated")
                            .apply { putUserData(DiffUserDataKeys.MERGE_EDITOR_FLAG, true) }
                    )
                }
            }
        }
    }

    private fun showInputDialog(message: String): String? {
        // Show input dialog
        val inputDialog = Messages.showInputDialog(message, "Refactoring Instructions", null)
        return inputDialog?.trim()
    }
}

fun preformRefactor(cxt: ReplaceContext): String? {
    val selection = cxt.selection
    val conv = Bots().refactor
    val doc = cxt.editor.document.text
    conv.addMessage("system", "Here is a code snippet the user is working on.\n" + doc)
    return conv.ask("Please refactor the following code:\n" + selection)?.firstMessage()
}

class RefactorAction : ReplaceWithDiffAction(::preformRefactor)

fun performImplement(cxt: ReplaceContext): String? {
    val selection = cxt.selection
    val doc = cxt.editor.document.text
    val conv = Bots().implementor
    conv.addMessage("system", "Here is a code snippet the user is working on.\n" + doc)
    return conv.ask("Please implement the following code:\n" + selection + "\nYou do not need to write the whole program. The summary of your work must be written in comments inside a program rather than separate text.")?.firstMessage()
}

class ImplementAction : ReplaceWithDiffAction(::performImplement)

fun performInstruction(cxt:InstructedReplaceContext): String? {
    val selection = cxt.selection
    val doc = cxt.editor.document.text
    val conv = Conversation(
            """Here is a code snippet the user is working on.
                |```
                |$selection
                |```
                |Please follow the instruction about the snippet given by the user.
                |Instruction: ${cxt.instruction}
            """.trimMargin()
    )
    return conv.generateResponse()?.firstMessage()
}
class InstructAction: InstructedReplaceWithDiffAction(::performInstruction)

class FindInjectedRunnablesAction: AnAction(){
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val helper = InjectedFunctionActionHelper(project)
        val configs = helper.findConfigurations(helper.getFilePath()!!)
        val pyconfigs = configs.values.flatten()
        pyconfigs.forEach { c -> helper.addConfig(c) }
    }

}

fun Editor.replaceSelectedText(text: String) {
    WriteCommandAction.runWriteCommandAction(project) {
        document.replaceString(selectionModel.selectionStart, selectionModel.selectionEnd, text)
    }
}


fun main() {
    val conversation = Bots().saria
    val resp = conversation.ask("やあサリア、調子は？")
    println(resp?.messages?.last()?.content)
    // get text input
    while (true) {
        readLine()?.let { conversation.ask(it) }.let { println(it?.messages?.last()?.content) }
    }
}