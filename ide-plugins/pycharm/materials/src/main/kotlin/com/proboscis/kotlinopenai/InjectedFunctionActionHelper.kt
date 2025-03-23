package com.proboscis.kotlinopenai

import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.execution.RunManager
import com.intellij.execution.RunnerAndConfigurationSettings
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.ExecutionUtil
import com.intellij.lang.parameterInfo.ParameterInfoContext
import com.intellij.notification.Notification
import com.intellij.notification.NotificationType
import com.intellij.notification.Notifications
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.actionSystem.impl.SimpleDataContext
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleManager
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.openapi.roots.ModuleRootManager
import com.intellij.psi.PsiFile
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.PyParameterInfoHandler
import com.jetbrains.python.actions.executeCodeInConsole
import com.jetbrains.python.console.PyExecuteConsoleCustomizer
import com.jetbrains.python.psi.*
import com.jetbrains.python.run.PythonConfigurationType
import com.jetbrains.python.run.PythonRunConfiguration
import com.jetbrains.python.sdk.PythonSdkUtil
import com.jetbrains.rd.util.getOrCreate
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.jetbrains.concurrency.AsyncPromise
import org.jetbrains.concurrency.Promise
import java.io.File
import java.util.concurrent.Executors


class InjectedFunctionActionHelper(val project: Project) {
    val first_module: Module = ModuleManager.getInstance(project).sortedModules[0]
    val sdk: Sdk? = PythonSdkUtil.findPythonSdk(first_module)
    val interpreterPath = sdk?.homePath
            ?: throw IllegalStateException("Python interpreter not found for the module:$first_module")
    val runManager = RunManager.getInstance(project)
    val runConfigurationType = getYourRunConfigurationType() // Replace this with your RunConfigurationType
    val factory: ConfigurationFactory = runConfigurationType.configurationFactories[0]

    //    val runConfigurationSettings: RunnerAndConfigurationSettings =
    //        runManager.createConfiguration("Generated Run Configuration", factory)
    val moduleManager = ModuleManager.getInstance(
            project
    )
    val log = Logger.getInstance("com.proboscis.chatgpt_experiment")
    val app = ApplicationManager.getApplication()


    private fun getYourRunConfigurationType(): PythonConfigurationType {
        /* Replace with logic to get your RunConfigurationType */
        val conf: PythonConfigurationType = PythonConfigurationType.getInstance()
        return conf
    }

    fun setupRunConfiguration(config: PythonRunConfiguration, src: PyConfiguration) {
        // Customize run configuration if necessary (e.g., set the main class, program arguments, etc.)
        config.scriptName = src.script_path
        config.sdkHome = src.interpreter_path
        config.interpreterOptions = ""
        config.scriptParameters = src.arguments.joinToString(" ")
        config.name = src.name
        config.workingDirectory = src.working_dir
        config.setEmulateTerminal(true)
        //set working dir to tmp
        val deps = getDependencies() + listOf(src.working_dir)
        config.setEnvs(mapOf("PYTHONPATH" to deps.joinToString(":")))
    }


    fun findConfigurations(modulePath: String): Map<String, List<PyConfiguration>> {
        // val args = "-m pinjected.run_config_utils create_configurations $modulePath".split(" ")
        assert(modulePath != "")
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations $modulePath".split(" ")
        return runPythonJson<ConfigurationWrapper>(args).configs
    }

    fun listCompletions(modulePath: String): List<CustomCompletion> {
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.list_completions $modulePath".split(" ")
        return runPythonJson<List<CustomCompletion>>(args)
    }

    fun designMetadata(modulePath: String): List<DesignMetadata> {
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.design_metadata $modulePath".split(" ")
        return runPythonJson<List<DesignMetadata>>(args)
    }


    fun runPython(pythonArgs: List<String>): String {
        // TODO check stderr
        val command = "$interpreterPath ${pythonArgs.joinToString(" ")}"
        log.info("Running command: $command")

        val deps = getDependencies()
        val (stdout, stderr, code) = runCommandWithEnvironment(
                command.split(" "), mapOf(
                "PYTHONPATH" to deps.joinToString(":")
        )
        )
        log.info("Output: $stdout")
        if (stderr.isNotEmpty()) {
            log.info("Error: from command: $command \n stderr=>\n$stderr")
        }

        if (code != 0) {
            throw IllegalStateException("Failed to run command: $command \n stderr=>\n$stderr")
        }
        return stdout
    }

    inline fun <reified T> runPythonJson(pythonArgs: List<String>): T {
        val stdout = runPython(pythonArgs)
        try {
            var json = stdout.trim()
            if (json.contains("<pinjected>")) {
                val pattern = Regex("<pinjected>(.*)</pinjected>", RegexOption.DOT_MATCHES_ALL)
                val match = pattern.find(stdout.trim())
                println("looking for pattern: $pattern in ${stdout.trim()} and got $match")
                json = match?.groupValues?.get(1) ?: throw IllegalStateException("Failed to parse json")
            }
            // for some reason stdout is empty...
            println("decoding json: ${stdout.trim()}")
            return Json.decodeFromString(json)
        } catch (e: Exception) {
            val command = "$interpreterPath ${pythonArgs.joinToString(" ")}"
            showNotification("Error Parsing Json!", "Exception -> ${e} ${e.message} when parsing output from: ${command}. \nstdout:${stdout}")
            throw e
        }
    }

    fun getFilePath(): String? {
        val fileEditorManager = FileEditorManager.getInstance(project)
        val virtualFile = fileEditorManager.selectedFiles.firstOrNull()
        return virtualFile?.path
    }

    fun runCommandWithEnvironment(
            command: List<String>,
            envVars: Map<String, String>,
            workingDirectory: File? = null
    ): Triple<String, String, Int> {
        val env = mutableMapOf<String, String>()
        env.putAll(System.getenv())

        // Modify or add environment variables
        for ((key, value) in envVars) {
            val currentValue = env[key]
            if (currentValue != null) {
                env[key] = "$currentValue:$value"
            } else {
                env[key] = value
            }
        }

        val processBuilder = ProcessBuilder(command)
        processBuilder.environment().putAll(env)

        if (workingDirectory != null) {
            processBuilder.directory(workingDirectory)
        } else{
            processBuilder.directory(File(System.getProperty("user.home")))
        }
        println("Running command: " + processBuilder.command().joinToString(" "))
        val process = processBuilder.start()


        println("Waiting for process to finish...")
        val outputBuffer = StringBuffer()
        val errorBuffer = StringBuffer()

        val executor = Executors.newFixedThreadPool(2)
        executor.submit {
            process.inputStream.bufferedReader().forEachLine {
                println("Output: $it")
                outputBuffer.appendLine(it)
            }
        }

        executor.submit {
            process.errorStream.bufferedReader().forEachLine {
                println("Error: $it")
                errorBuffer.appendLine(it)
            }
        }


        val exitCode = process.waitFor()
        executor.shutdown()
        val output = outputBuffer.toString()
        val errorOutput = errorBuffer.toString()

        println("Output: $output")
        println("Error: $errorOutput")

        return Triple(output, errorOutput, exitCode)
    }

    fun getModuleSourceRoots(): List<String> = app.runReadAction<List<String>> {
        val moduleManager = ModuleManager.getInstance(project)
        val roots = moduleManager.modules.flatMap {
            val mrm = ModuleRootManager.getInstance(it)
            mrm.sourceRoots.filter { !mrm.fileIndex.isInTestSourceContent(it) }.map { it.url }
        }
        roots.map { it.replace("file://", "") }
    }

    fun getDependencies(): List<String> = app.runReadAction<List<String>> {
        val deps = mutableSetOf<String>()
        for (module in moduleManager.modules) {
            val moduleRootManager = ModuleRootManager.getInstance(module)
            for (contentRoot in moduleRootManager.contentRootUrls) {
                // contentRoot starts from file:// so we need to remove that.
                println("Module: " + module.name + " - Root Path: " + contentRoot)
                deps.add(contentRoot.replace("file://", ""))
            }
        }
        // Good, now this contains all the possible paths including not true ones.
        // we can start from here and see if we can get the correct paths.
        // actually let's check for __init__ file existence to obtain the root dir of a module.
        fun containsInit(path: String): Boolean {
            val initFile = File(path, "__init__.py")
            return initFile.exists()
        }

        fun findPyModuleRoot(path: String): List<String> {
            /**
             * Given a path, find the root of the python module.
             * first look at current path, if it has __init__.py, check parent until it doesn't have __init__.py
             * then return the path.
             * if it doesn't have __init__.py, find the child that has __init__.py and return that path.
             * This algorithm requires revise.
             * It should actually check for several depths.
             * we should use breadth first search to find the roots.
             * or, we can just use the directories marked as sources.
             */
            if (containsInit(path)) {
                val parent = File(path).parentFile ?: return emptyList()
                return findPyModuleRoot(parent.absolutePath)
            } else {
                val children = File(path).listFiles() ?: return emptyList()
                for (child in children) {
                    if (child.isDirectory && containsInit(child.absolutePath)) {
                        return listOf(path)
                    }
                }
                return emptyList()
            }
        }

        val roots = deps.map { findPyModuleRoot(it) }.flatten() + getModuleSourceRoots()
        // We should also consider the directory marked as sources.

        println("Roots: $roots")
        roots.toSet().toList()
    }

    fun createRunConfig(): RunnerAndConfigurationSettings {
        val runConfigurationSettings = runManager.createConfiguration("Generated Run Configuration", factory)
        return runConfigurationSettings
    }

    fun runConfig(conf: PyConfiguration) {
        val config = addConfig(conf)
        runManager.selectedConfiguration = config
        // Run the configuration
        ExecutionUtil.runConfiguration(config, DefaultRunExecutor.getRunExecutorInstance())
    }

    fun addConfig(conf: PyConfiguration): RunnerAndConfigurationSettings {
        val runConfiguration = createRunConfig()
        setupRunConfiguration(runConfiguration.configuration as PythonRunConfiguration, conf)
        runManager.addConfiguration(runConfiguration)
        return runConfiguration
    }


    fun configurations(): Map<String, List<PyConfiguration>> {
        val filePath = getFilePath() ?: throw IllegalStateException("File not found")
        val confs = findConfigurations(filePath)
        return confs
    }


    fun runConfig(confName: String) {
        val confs = configurations()
        val conf = confs[confName]?.first()
                ?: throw IllegalStateException("Configuration not found. Probably missing the design to use.")
        runConfig(conf)
    }


    fun showNotification(title: String, content: String, type: NotificationType = NotificationType.ERROR) {
        val notification = Notification(
                "InjectedFunctionRunner",
                title,
                content,
                type
        )
        Notifications.Bus.notify(notification, project)
    }

    fun runInBackground(
            taskTitle: String,
            timeConsumingOperation: () -> Unit
    ) {
        val backgroundTask = object : Task.Backgroundable(project, taskTitle, true) {
            override fun run(indicator: ProgressIndicator) {
                indicator.isIndeterminate = true
                timeConsumingOperation()
            }
        }
        ProgressManager.getInstance().run(backgroundTask)
    }

    fun <T> runInBackground(taskTitle: String, task: (ProgressIndicator) -> T): Promise<T> {
        val promise = AsyncPromise<T>()

        val backgroundTask = object : Task.Backgroundable(project, taskTitle, true) {
            override fun run(indicator: ProgressIndicator) {
                try {
                    val result = task(indicator)
                    promise.setResult(result)
                } catch (e: Exception) {
                    showNotification("Error in background task", e.message ?: "Unknown error ($e)")
                    promise.setError(e)
                }
            }
        }

        ProgressManager.getInstance().run(backgroundTask)
        return promise
    }

    fun cachedConfigurations(name: String): Promise<List<PyConfiguration>> {
        val results = runInBackground("Find Configurations") { indicator ->
            indicator.fraction = 0.1
            // now where do I store cache?
            val filePath = getFilePath()!!
            var loaded = false

            var configs = InjectedFunctionActionHelperObject.cache.getOrCreate(filePath) { key ->
                loaded = true
                findConfigurations(key)
            }
            indicator.fraction = 0.5
            if (!configs.containsKey(name) and !loaded) {
                configs = findConfigurations(filePath)
                InjectedFunctionActionHelperObject.cache[filePath] = configs
            }
            indicator.fraction = 0.9
            val config_list = configs[name]!!
            indicator.fraction = 1.0
            config_list
        }
        return results
    }

    fun createRunActionsCached(name: String): Promise<List<ActionItem>> {
        return cachedConfigurations(name).then {
            it.map { conf ->
                ActionItem(conf.name) {
                    runConfig(conf)
                }
            }
        }
    }

    fun updateConfigurations() {
        val filePath = getFilePath() ?: throw IllegalStateException("File not found")
        val confs = findConfigurations(filePath)
        InjectedFunctionActionHelperObject.cache[filePath] = confs
    }
}

fun executeScriptInConsole(project: Project, script: String, editor: Editor?) {
    val consoleCustomizer = PyExecuteConsoleCustomizer.Companion.instance
    val pythonRunConfiguration = consoleCustomizer.getContextConfig(SimpleDataContext.getProjectContext(project))
    executeCodeInConsole(project, script, editor, true, true, false, pythonRunConfiguration)
}


class TestExecuteScriptAction : AnAction("Execute Test Script") {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val helper = InjectedFunctionActionHelper(project)
        val pinjectedUtil = PinjectedConsoleUtil(helper)
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        pinjectedUtil.runInjected(
                "/Users/s22625/repos/pinject-design/pinjected/ide_supports/console_run_helper.py",
                "run_test",
                editor
        )
        return
//        val testScript = "print('Hello from test script!')"
//
//        executeScriptInConsole(project, testScript, editor)
    }
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
                        // Check if the target has a type annotation (PEP 526)
                        val annotation = it.annotation
                        //if (annotation != null && annotation.text.contains("Injected")) {
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
@Serializable
data class CodeBlock(
        val code: String
)

class PinjectedConsoleUtil(
        val helper: InjectedFunctionActionHelper
) {
    fun runInjected(scriptPath: String, funcName: String, editor: Editor? = null) {
        val args = "-m pinjected.ide_supports.console_run_helper generate-code-with-reload $scriptPath $funcName".split(" ")
        val block: CodeBlock = helper.runPythonJson<CodeBlock>(args)
        // now what do I do ...
        executeScriptInConsole(helper.project, block.code, editor)

    }
}


