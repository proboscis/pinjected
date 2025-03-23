package com.proboscis.pinjectdesign.kotlin

import com.proboscis.pinjectdesign.kotlin.data.ActionItem
import com.proboscis.pinjectdesign.kotlin.data.CodeBlock
import com.proboscis.pinjectdesign.kotlin.data.ConfigurationWrapper
import com.proboscis.pinjectdesign.kotlin.data.CustomCompletion
import com.proboscis.pinjectdesign.kotlin.data.DesignMetadata
import com.proboscis.pinjectdesign.kotlin.data.PyConfiguration
import com.intellij.execution.RunManager
import com.intellij.execution.RunnerAndConfigurationSettings
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.ExecutionUtil
import com.intellij.notification.Notification
import com.intellij.notification.NotificationType
import com.intellij.notification.Notifications
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleManager
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.openapi.roots.ModuleRootManager
import com.jetbrains.python.run.PythonConfigurationType
import com.jetbrains.python.run.PythonRunConfiguration
import com.jetbrains.python.sdk.PythonSdkUtil
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import org.jetbrains.concurrency.AsyncPromise
import org.jetbrains.concurrency.Promise
import java.io.File
import java.util.concurrent.Executors

object InjectedFunctionActionHelperObject {
    val cache = mutableMapOf<String, Map<String, List<PyConfiguration>>>()
}

class InjectedFunctionActionHelper(val project: Project) {
    val first_module: Module = ModuleManager.getInstance(project).sortedModules[0]
    val sdk: Sdk? = PythonSdkUtil.findPythonSdk(first_module)
    val interpreterPath = sdk?.homePath
            ?: throw IllegalStateException("Python interpreter not found for the module:$first_module")
    val runManager = RunManager.getInstance(project)
    val runConfigurationType = getYourRunConfigurationType() // Replace this with your RunConfigurationType
    val factory: ConfigurationFactory = runConfigurationType.configurationFactories[0]
    val moduleManager = ModuleManager.getInstance(project)
    val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin")
    val app = ApplicationManager.getApplication()

    private fun getYourRunConfigurationType(): PythonConfigurationType {
        return PythonConfigurationType.getInstance()
    }

    fun setupRunConfiguration(config: PythonRunConfiguration, src: PyConfiguration) {
        config.scriptName = src.script_path
        config.sdkHome = src.interpreter_path
        config.interpreterOptions = ""
        config.scriptParameters = src.arguments.joinToString(" ")
        config.name = src.name
        config.workingDirectory = src.working_dir
        config.setEmulateTerminal(true)
        val deps = getDependencies() + listOf(src.working_dir)
        config.setEnvs(mapOf("PYTHONPATH" to deps.joinToString(":")))
    }

    fun findConfigurations(modulePath: String): Map<String, List<PyConfiguration>> {
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
                println("Module: " + module.name + " - Root Path: " + contentRoot)
                deps.add(contentRoot.replace("file://", ""))
            }
        }

        fun containsInit(path: String): Boolean {
            val initFile = File(path, "__init__.py")
            return initFile.exists()
        }

        fun findPyModuleRoot(path: String): List<String> {
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
            val filePath = getFilePath()!!
            var loaded = false

            var configs = InjectedFunctionActionHelperObject.cache.getOrPut(filePath) {
                loaded = true
                findConfigurations(filePath)
            }
            indicator.fraction = 0.5
            if (!configs.containsKey(name) && !loaded) {
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
