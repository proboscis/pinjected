package com.proboscis.pinjectdesign.helpers

import com.intellij.execution.RunManager
import com.intellij.execution.configurations.ConfigurationFactory
import com.intellij.execution.configurations.RunConfiguration
import com.intellij.execution.impl.RunnerAndConfigurationSettingsImpl
import com.intellij.notification.Notification
import com.intellij.notification.NotificationType
import com.intellij.notification.Notifications
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleManager
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.projectRoots.Sdk
import com.jetbrains.python.run.PythonConfigurationType
import com.jetbrains.python.run.PythonRunConfiguration
import com.jetbrains.python.sdk.PythonSdkUtil
import kotlinx.serialization.json.Json
import org.jetbrains.concurrency.Promise
import org.jetbrains.concurrency.resolvedPromise
import java.io.File
import java.nio.file.Path
import com.proboscis.pinjectdesign.config.PyConfiguration
import com.proboscis.pinjectdesign.config.ConfigurationWrapper

fun <K, V> MutableMap<K, V>.getOrCreate(key: K, factory: (K) -> V): V {
    return this[key] ?: run {
        val value = factory(key)
        this[key] = value
        value
    }
}

class InjectedFunctionActionHelper(val project: Project) {
    val first_module: Module = ModuleManager.getInstance(project).sortedModules[0]
    val sdk: Sdk? = PythonSdkUtil.findPythonSdk(first_module)
    val interpreterPath = sdk?.homePath
            ?: throw IllegalStateException("Python interpreter not found for the module:$first_module")
    val runManager = RunManager.getInstance(project)
    val runConfigurationType = getYourRunConfigurationType()
    val factory: ConfigurationFactory = runConfigurationType.configurationFactories[0]

    val moduleManager = ModuleManager.getInstance(project)
    val log = Logger.getInstance("com.cyberagent.ailab.pinjectdesign")
    val app = ApplicationManager.getApplication()

    private fun getYourRunConfigurationType(): PythonConfigurationType {
        val conf: PythonConfigurationType = PythonConfigurationType.getInstance()
        return conf
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

    fun getDependencies(): List<String> {
        val modules = moduleManager.sortedModules
        val dependencies = mutableListOf<String>()
        for (module in modules) {
            val moduleFile = module.moduleFile
            if (moduleFile != null) {
                val moduleDir = moduleFile.parent
                dependencies.add(moduleDir.path)
            }
        }
        return dependencies
    }

    fun getFilePath(): String? {
        val editor = com.intellij.openapi.fileEditor.FileEditorManager.getInstance(project).selectedTextEditor
        val virtualFile = editor?.document?.let { document ->
            com.intellij.openapi.fileEditor.FileDocumentManager.getInstance().getFile(document)
        }
        return virtualFile?.path
    }

    inline fun <reified T> runPythonJson(args: List<String>): T {
        val result = runPython(args)
        val jsonStart = result.indexOf("<pinjected>")
        val jsonEnd = result.indexOf("</pinjected>")
        if (jsonStart == -1 || jsonEnd == -1) {
            throw RuntimeException("Could not find pinjected tags in output: $result")
        }
        val jsonStr = result.substring(jsonStart + "<pinjected>".length, jsonEnd)
        return Json.decodeFromString<T>(jsonStr)
    }

    fun runPython(args: List<String>): String {
        val processBuilder = ProcessBuilder(listOf(interpreterPath) + args)
        processBuilder.directory(File(project.basePath ?: System.getProperty("user.dir")))
        val process = processBuilder.start()
        val output = process.inputStream.bufferedReader().readText()
        val errorOutput = process.errorStream.bufferedReader().readText()
        process.waitFor()
        if (process.exitValue() != 0) {
            throw RuntimeException("Python process failed with exit code ${process.exitValue()}: $errorOutput")
        }
        return output
    }

    fun runConfig(conf: PyConfiguration) {
        val runConfiguration = createRunConfiguration(conf)
        val executor = com.intellij.execution.executors.DefaultRunExecutor.getRunExecutorInstance()
        com.intellij.execution.ProgramRunnerUtil.executeConfiguration(runConfiguration, executor)
    }

    private fun createRunConfiguration(conf: PyConfiguration): RunnerAndConfigurationSettingsImpl {
        val runConfiguration = runManager.createConfiguration(conf.name, factory) as RunnerAndConfigurationSettingsImpl
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
        var result: T? = null
        val backgroundTask = object : Task.Modal(project, taskTitle, true) {
            override fun run(indicator: ProgressIndicator) {
                try {
                    result = task(indicator)
                } catch (e: Exception) {
                    showNotification("Error in background task", e.message ?: "Unknown error ($e)")
                    throw e
                }
            }
        }
        ProgressManager.getInstance().run(backgroundTask)
        return resolvedPromise(result!!)
    }

    fun cachedConfigurations(name: String): Promise<List<PyConfiguration>> {
        return runInBackground("Find Configurations") { indicator ->
            indicator.fraction = 0.1
            val filePath = getFilePath()!!
            var loaded = false

            var configs = com.proboscis.pinjectdesign.config.InjectedFunctionActionHelperObject.cache.getOrCreate(filePath) { key ->
                loaded = true
                findConfigurations(key)
            }
            indicator.fraction = 0.5
            if (!configs.containsKey(name) && !loaded) {
                configs = findConfigurations(filePath)
                com.proboscis.pinjectdesign.config.InjectedFunctionActionHelperObject.cache[filePath] = configs
            }
            indicator.fraction = 0.9
            val config_list = configs[name]!!
            indicator.fraction = 1.0
            config_list
        }
    }

    fun createRunActionsCached(name: String): Promise<List<com.proboscis.pinjectdesign.lineMarkers.ActionItem>> {
        return cachedConfigurations(name).then { configs ->
            configs.map { conf ->
                com.proboscis.pinjectdesign.lineMarkers.ActionItem(conf.name) {
                    runConfig(conf)
                }
            }
        }
    }

    fun updateConfigurations() {
        val filePath = getFilePath() ?: throw IllegalStateException("File not found")
        val confs = findConfigurations(filePath)
        com.proboscis.pinjectdesign.config.InjectedFunctionActionHelperObject.cache[filePath] = confs
    }
}
