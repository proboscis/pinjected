package com.proboscis.pinjectdesign.kotlin

import com.proboscis.pinjectdesign.kotlin.data.ActionItem
import com.proboscis.pinjectdesign.kotlin.data.CodeBlock
import com.proboscis.pinjectdesign.kotlin.data.ConfigurationWrapper
import com.proboscis.pinjectdesign.kotlin.data.CustomCompletion
import com.proboscis.pinjectdesign.kotlin.data.DesignMetadata
import com.proboscis.pinjectdesign.kotlin.data.PyConfiguration
import com.proboscis.pinjectdesign.kotlin.error.ErrorHandler
import com.proboscis.pinjectdesign.kotlin.error.ErrorHandler.ErrorContext
import com.proboscis.pinjectdesign.kotlin.error.ErrorHandler.ErrorType
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
    
    /**
     * Safely creates an InjectedFunctionActionHelper or returns null if Python is not configured.
     * Shows appropriate error messages to the user.
     */
    fun createSafely(project: Project?): InjectedFunctionActionHelper? {
        if (project == null) return null
        
        return try {
            InjectedFunctionActionHelper(project)
        } catch (e: Exception) {
            // Error is already shown by InjectedFunctionActionHelper constructor
            null
        }
    }
}

open class InjectedFunctionActionHelper(val project: Project) {
    val first_module: Module = ModuleManager.getInstance(project).sortedModules[0]
    val sdk: Sdk? = PythonSdkUtil.findPythonSdk(first_module)
    open val interpreterPath = sdk?.homePath ?: run {
        val error = ErrorContext(
            ErrorType.PYTHON_NOT_FOUND,
            "No Python interpreter configured for the project",
            details = "Module: ${first_module.name}"
        )
        ErrorHandler.handleError(project, error)
        throw IllegalStateException("Python interpreter not found for the module:$first_module")
    }
    val runManager = RunManager.getInstance(project)
    val runConfigurationType = getYourRunConfigurationType() // Replace this with your RunConfigurationType
    val factory: ConfigurationFactory = runConfigurationType.configurationFactories[0]
    val moduleManager = ModuleManager.getInstance(project)
    val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin")
    val app = ApplicationManager.getApplication()
    
    // Store last command output for error reporting
    var lastStdout: String? = null
    var lastStderr: String? = null
    
    // Cache for pinjected main path
    private var cachedPinjectedMainPath: String? = null

    private fun getYourRunConfigurationType(): PythonConfigurationType {
        return PythonConfigurationType.getInstance()
    }

    /**
     * Find the path to pinjected's __main__.py file.
     * This is used to run pinjected commands directly.
     * Results are cached to avoid repeated Python subprocess calls.
     * 
     * @param forceRefresh If true, ignores the cache and finds the path again
     * @return The absolute path to pinjected/__main__.py
     * @throws RuntimeException if the path cannot be found
     */
    fun findPinjectedMainPath(forceRefresh: Boolean = false): String {
        // Return cached value if available and not forcing refresh
        if (!forceRefresh && cachedPinjectedMainPath != null) {
            log.info("Using cached pinjected __main__.py path: $cachedPinjectedMainPath")
            return cachedPinjectedMainPath!!
        }
        
        log.info("Finding pinjected __main__.py path...")
        
        // First try to import pinjected.__main__ directly
        val directCommand = listOf(
            interpreterPath,
            "-c",
            "import pinjected.__main__; print(pinjected.__main__.__file__)"
        )
        
        try {
            val process = ProcessBuilder(directCommand)
                .directory(File(project.basePath ?: "."))
                .start()
            
            val mainPath = process.inputStream.bufferedReader().use { it.readText().trim() }
            val exitCode = process.waitFor(5, java.util.concurrent.TimeUnit.SECONDS)
            
            if (exitCode && process.exitValue() == 0 && mainPath.isNotEmpty()) {
                log.info("Found pinjected __main__.py at: $mainPath")
                cachedPinjectedMainPath = mainPath  // Cache the result
                return mainPath
            }
        } catch (e: Exception) {
            log.warn("Failed to find __main__.py via direct import: ${e.message}")
        }
        
        // Fallback: find via pinjected module directory
        val fallbackCommand = listOf(
            interpreterPath,
            "-c",
            "import pinjected; import os; print(os.path.join(os.path.dirname(pinjected.__file__), '__main__.py'))"
        )
        
        try {
            val process = ProcessBuilder(fallbackCommand)
                .directory(File(project.basePath ?: "."))
                .start()
            
            val fallbackPath = process.inputStream.bufferedReader().use { it.readText().trim() }
            val exitCode = process.waitFor(5, java.util.concurrent.TimeUnit.SECONDS)
            
            if (exitCode && process.exitValue() == 0 && fallbackPath.isNotEmpty()) {
                log.info("Found pinjected __main__.py via fallback at: $fallbackPath")
                cachedPinjectedMainPath = fallbackPath  // Cache the result
                return fallbackPath
            }
        } catch (e: Exception) {
            log.error("Failed to find __main__.py via fallback: ${e.message}")
        }
        
        throw RuntimeException("Could not find pinjected __main__.py - is pinjected installed?")
    }
    
    /**
     * Clear the cached pinjected main path.
     * Useful when the Python environment changes.
     */
    fun clearPinjectedMainPathCache() {
        cachedPinjectedMainPath = null
        log.info("Cleared pinjected __main__.py path cache")
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

    open fun findConfigurations(modulePath: String): Map<String, List<PyConfiguration>> {
        log.info("=== findConfigurations START ===")
        log.info("Module path: $modulePath")
        log.info("Python interpreter: $interpreterPath")
        
        assert(modulePath != "") { "Module path cannot be empty" }
        
        // Check if file exists
        val moduleFile = File(modulePath)
        if (!moduleFile.exists()) {
            log.error("Module file does not exist: $modulePath")
            val error = ErrorContext(
                ErrorType.MODULE_NOT_FOUND,
                "The Python file does not exist",
                details = modulePath
            )
            ErrorHandler.handleError(project, error)
            throw IllegalArgumentException("Module file does not exist: $modulePath")
        }
        
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations $modulePath".split(" ")
        val command = "$interpreterPath ${args.joinToString(" ")}"
        log.info("Python command args: $args")
        
        try {
            log.info("Executing Python command...")
            val wrapper = runPythonJson<ConfigurationWrapper>(args)
            val configs = wrapper.configs
            
            log.info("Successfully parsed configurations")
            log.info("Found ${configs.size} configuration groups")
            
            // Log details of each configuration
            configs.forEach { (name, configList) ->
                log.info("Configuration group '$name' has ${configList.size} configs:")
                configList.forEachIndexed { index, config ->
                    log.info("  [$index] ${config.name}")
                    log.info("      script: ${config.script_path}")
                    log.info("      args: ${config.arguments}")
                    log.info("      working_dir: ${config.working_dir}")
                }
            }
            
            log.info("=== findConfigurations END ===")
            return configs
            
        } catch (e: Exception) {
            log.error("=== findConfigurations ERROR ===", e)
            log.error("Failed to find configurations for: $modulePath")
            log.error("Error type: ${e.javaClass.simpleName}")
            log.error("Error message: ${e.message}")
            
            // Analyze and show user-friendly error
            val errorContext = ErrorHandler.analyzeException(e, command)
            val enhancedContext = when (errorContext.type) {
                ErrorType.CONFIGURATION_EXTRACTION_FAILED -> errorContext.copy(
                    details = modulePath,
                    stdout = lastStdout,
                    stderr = lastStderr
                )
                else -> errorContext.copy(
                    details = modulePath
                )
            }
            
            ErrorHandler.handleError(project, enhancedContext)
            throw e
        }
    }

    fun listCompletions(modulePath: String): List<CustomCompletion> {
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.list_completions $modulePath".split(" ")
        return runPythonJson<List<CustomCompletion>>(args)
    }

    fun designMetadata(modulePath: String): List<DesignMetadata> {
        val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.design_metadata $modulePath".split(" ")
        return runPythonJson<List<DesignMetadata>>(args)
    }

    open fun runPython(pythonArgs: List<String>): String {
        val command = "$interpreterPath ${pythonArgs.joinToString(" ")}"
        log.info("=== runPython START ===")
        log.info("Full command: $command")
        log.info("Working directory: ${project?.basePath ?: System.getProperty("user.home")}")
        
        val deps = getDependencies()
        log.info("Dependencies for PYTHONPATH: ${deps.joinToString(":")}")
        
        val (stdout, stderr, code) = runCommandWithEnvironment(
                command.split(" "), mapOf(
                "PYTHONPATH" to deps.joinToString(":")
        )
        )
        
        // Store for error reporting
        lastStdout = stdout
        lastStderr = stderr
        
        log.info("Exit code: $code")
        if (stdout.isNotEmpty()) {
            log.info("Standard output (${stdout.length} chars):")
            log.info(stdout.take(1000)) // Log first 1000 chars
            if (stdout.length > 1000) {
                log.info("... (truncated, ${stdout.length - 1000} more chars)")
            }
        }
        if (stderr.isNotEmpty()) {
            log.warn("Standard error: $stderr")
        }

        if (code != 0) {
            log.error("Command failed with exit code $code")
            log.error("Command was: $command")
            log.error("Stderr: $stderr")
            
            // Show user-friendly error
            val errorContext = ErrorHandler.analyzeException(
                IllegalStateException("Failed to run command: $command \n stderr=>\n$stderr"),
                command
            ).copy(stdout = stdout, stderr = stderr)
            
            ErrorHandler.handleError(project, errorContext)
            
            throw IllegalStateException("Failed to run command: $command \n stderr=>\n$stderr")
        }
        
        log.info("=== runPython END ===")
        return stdout
    }

    inline fun <reified T> runPythonJson(pythonArgs: List<String>): T {
        log.info("=== runPythonJson START ===")
        log.info("Expected type: ${T::class.simpleName}")
        
        val stdout = runPython(pythonArgs)
        try {
            var json = stdout.trim()
            log.info("Raw output length: ${stdout.length}")
            
            if (json.contains("<pinjected>")) {
                log.info("Found <pinjected> tags, extracting JSON...")
                val pattern = Regex("<pinjected>(.*?)</pinjected>", RegexOption.DOT_MATCHES_ALL)
                val match = pattern.find(json)
                if (match != null) {
                    json = match.groupValues[1].trim()
                    log.info("Extracted JSON (${json.length} chars): ${json.take(500)}")
                    if (json.length > 500) {
                        log.info("... (truncated)")
                    }
                } else {
                    log.error("Failed to find <pinjected> content in output")
                    throw IllegalStateException("Failed to parse JSON from <pinjected> tags")
                }
            } else {
                log.info("No <pinjected> tags found, using raw output as JSON")
            }
            
            log.info("Attempting to decode JSON...")
            val result = Json.decodeFromString<T>(json)
            log.info("Successfully decoded to ${result!!::class.simpleName}")
            log.info("=== runPythonJson END ===")
            return result
            
        } catch (e: Exception) {
            log.error("=== runPythonJson ERROR ===")
            log.error("Failed to parse JSON", e)
            log.error("Raw stdout: $stdout")
            
            val command = "$interpreterPath ${pythonArgs.joinToString(" ")}"
            
            // Show user-friendly error
            val errorContext = ErrorContext(
                ErrorType.JSON_PARSING_FAILED,
                "Failed to parse response from pinjected",
                exception = e,
                command = command,
                stdout = stdout,
                stderr = lastStderr
            )
            
            ErrorHandler.handleError(project, errorContext)
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
        log.info("=== cachedConfigurations START for '$name' ===")
        
        val results = runInBackground("Find Configurations") { indicator ->
            indicator.fraction = 0.1
            val filePath = getFilePath()
            log.info("File path: $filePath")
            
            if (filePath == null) {
                log.error("No file path available")
                throw IllegalStateException("No file selected")
            }
            
            var loaded = false

            log.info("Checking cache for file: $filePath")
            var configs = InjectedFunctionActionHelperObject.cache.getOrPut(filePath) {
                log.info("Cache miss - loading configurations from Python")
                loaded = true
                findConfigurations(filePath)
            }
            
            if (!loaded) {
                log.info("Found cached configurations: ${configs.keys}")
            }
            
            indicator.fraction = 0.5
            
            // Check if the requested configuration exists
            if (!configs.containsKey(name)) {
                log.warn("Configuration '$name' not found in cache")
                if (!loaded) {
                    log.info("Reloading configurations from Python")
                    configs = findConfigurations(filePath)
                    InjectedFunctionActionHelperObject.cache[filePath] = configs
                    log.info("After reload, configurations: ${configs.keys}")
                }
            }
            
            indicator.fraction = 0.9
            
            val configList = configs[name]
            if (configList == null) {
                log.error("Configuration '$name' not found even after reload")
                log.error("Available configurations: ${configs.keys}")
                
                // Show user-friendly notification about the mismatch
                val availableKeys = configs.keys.sorted().joinToString("\n• ", prefix = "• ")
                val message = """
                    |Configuration key mismatch!
                    |
                    |Looking for: "$name"
                    |
                    |Available configurations:
                    |$availableKeys
                    |
                    |This may happen if the function name doesn't match the configuration key.
                """.trimMargin()
                
                showNotification(
                    "Configuration Not Found", 
                    message,
                    NotificationType.WARNING
                )
                
                return@runInBackground emptyList<PyConfiguration>()
            }
            
            log.info("Found ${configList.size} configurations for '$name'")
            indicator.fraction = 1.0
            
            log.info("=== cachedConfigurations END ===")
            configList
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
        log.info("=== updateConfigurations START ===")
        val filePath = getFilePath()
        log.info("Current file path: $filePath")
        
        if (filePath == null) {
            log.error("No file selected in editor")
            throw IllegalStateException("No file selected - please open a Python file")
        }
        
        try {
            log.info("Clearing cache for: $filePath")
            InjectedFunctionActionHelperObject.cache.remove(filePath)
            
            log.info("Finding new configurations...")
            val confs = findConfigurations(filePath)
            
            log.info("Updating cache with ${confs.size} configuration groups")
            InjectedFunctionActionHelperObject.cache[filePath] = confs
            
            // Log cache status
            log.info("Cache now contains configurations for ${InjectedFunctionActionHelperObject.cache.size} files")
            InjectedFunctionActionHelperObject.cache.forEach { (path, configs) ->
                log.info("  $path -> ${configs.size} groups")
            }
            
            // Show detailed notification about what was found
            val totalConfigs = confs.values.sumOf { it.size }
            val configKeys = confs.keys.sorted().take(10).joinToString(", ")
            val moreText = if (confs.size > 10) " (and ${confs.size - 10} more)" else ""
            
            showNotification(
                "Configurations Updated",
                "Found $totalConfigs configurations in ${confs.size} groups: $configKeys$moreText",
                NotificationType.INFORMATION
            )
            
        } catch (e: Exception) {
            log.error("Failed to update configurations", e)
            
            // The error has already been shown by findConfigurations,
            // but we can add additional context if needed
            if (e.message?.contains("Python interpreter not found") == false &&
                e.message?.contains("No module named 'pinjected'") == false) {
                // Only show additional error if it's not already handled
                val errorContext = ErrorContext(
                    ErrorType.CACHE_ERROR,
                    "Failed to update configuration cache",
                    exception = e,
                    details = filePath
                )
                ErrorHandler.handleError(project, errorContext)
            }
            
            throw e
        } finally {
            log.info("=== updateConfigurations END ===")
        }
    }
}
