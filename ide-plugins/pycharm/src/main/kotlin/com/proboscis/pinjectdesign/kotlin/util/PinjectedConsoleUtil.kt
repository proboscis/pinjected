package com.proboscis.pinjectdesign.kotlin.util

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.data.CodeBlock
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.jetbrains.python.actions.executeCodeInConsole
import com.jetbrains.python.console.PyExecuteConsoleCustomizer
import com.intellij.openapi.actionSystem.impl.SimpleDataContext

class PinjectedConsoleUtil(
    val helper: InjectedFunctionActionHelper
) {
    fun runInjected(scriptPath: String, funcName: String, editor: Editor? = null) {
        val args = "-m pinjected.ide_supports.console_run_helper generate-code-with-reload $scriptPath $funcName".split(" ")
        val block: CodeBlock = helper.runPythonJson<CodeBlock>(args)
        executeScriptInConsole(helper.project, block.code, editor)
    }
    
    fun runPinjectedCommand(scriptPath: String, funcName: String, command: String) {
        val args = "-m pinjected.ide_supports.console_run_helper $command $scriptPath $funcName".split(" ")
        val block: CodeBlock = helper.runPythonJson<CodeBlock>(args)
        executeScriptInConsole(helper.project, block.code, null)
    }
}

fun executeScriptInConsole(project: Project, script: String, editor: Editor?) {
    val consoleCustomizer = PyExecuteConsoleCustomizer.Companion.instance
    val pythonRunConfiguration = consoleCustomizer.getContextConfig(SimpleDataContext.getProjectContext(project))
    executeCodeInConsole(project, script, editor, true, true, false, pythonRunConfiguration)
}
