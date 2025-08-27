package com.proboscis.pinjectdesign.kotlin.util

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelperObject
import com.proboscis.pinjectdesign.kotlin.data.ActionItem
import com.proboscis.pinjectdesign.kotlin.data.PyConfiguration
import com.proboscis.pinjectdesign.kotlin.error.DiagnosticRunner
import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.actionSystem.*
import com.intellij.openapi.actionSystem.impl.SimpleDataContext
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.fileEditor.FileDocumentManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.psi.PsiElement
import com.intellij.psi.util.PsiTreeUtil
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.PySubscriptionExpression
import com.jetbrains.python.psi.PyReferenceExpression
import com.jetbrains.python.psi.PyAnnotation
import com.jetbrains.python.psi.PyFile
import java.awt.event.MouseEvent

/**
 * Enhanced utility for handling gutter actions with grouped menu support.
 */
object GutterActionUtilEnhanced {
    private val LOG = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.util.GutterActionUtilEnhanced")
    
    /**
     * Shows a hierarchical popup menu with grouped actions.
     */
    fun showHierarchicalPopup(
        e: MouseEvent?,
        project: Project,
        name: String,
        element: PsiElement?
    ) {
        println("[IProxy Debug] Creating hierarchical menu for: $name")
        println("[IProxy Debug] Element type: ${element?.javaClass?.simpleName}")
        println("[IProxy Debug] Element text: ${element?.text}")
        println("[IProxy Debug] Element node type: ${element?.node?.elementType}")
        
        LOG.debug("Creating hierarchical menu for: $name")
        LOG.debug("Element type: ${element?.javaClass?.simpleName}")
        LOG.debug("Element text: ${element?.text}")
        LOG.debug("Element node type: ${element?.node?.elementType}")
        
        // Create the action group
        val mainGroup = DefaultActionGroup("Pinjected Actions", true)
        
        // Check if this is an IProxy variable - try multiple ways
        var iproxyType: String? = null
        
        if (element != null) {
            println("[IProxy Debug] Attempting to extract IProxy type...")
            
            // First try to get the PyTargetExpression
            var targetExpr = PsiTreeUtil.getParentOfType(element, PyTargetExpression::class.java)
            println("[IProxy Debug] Direct parent PyTargetExpression: ${targetExpr?.name}")
            
            // If element itself is not under a target expression, maybe it's the name of one
            if (targetExpr == null && element.text == name) {
                println("[IProxy Debug] No direct parent, searching siblings...")
                // Try to find a sibling or nearby target expression with this name
                val parent = element.parent
                println("[IProxy Debug] Parent element: ${parent?.javaClass?.simpleName}")
                if (parent != null) {
                    val targets = PsiTreeUtil.findChildrenOfType(parent, PyTargetExpression::class.java)
                    println("[IProxy Debug] Found ${targets.size} PyTargetExpressions in parent")
                    targetExpr = targets.find { it.name == name }
                    if (targetExpr != null) {
                        println("[IProxy Debug] Found matching target: ${targetExpr.name}")
                    }
                }
            }
            
            if (targetExpr != null) {
                println("[IProxy Debug] Found target expression: ${targetExpr.name}")
                LOG.debug("Found target expression: ${targetExpr.name}")
                iproxyType = extractIProxyTypeFromTargetExpression(targetExpr)
                println("[IProxy Debug] Extracted type from target expression: $iproxyType")
                LOG.debug("Extracted type from target expression: $iproxyType")
            } else {
                println("[IProxy Debug] No target expression found for element")
                LOG.debug("No target expression found for element")
            }
        }
        
        println("[IProxy Debug] Final extracted IProxy type: $iproxyType")
        LOG.debug("Final extracted IProxy type: $iproxyType")
        
        if (iproxyType != null) {
            LOG.debug("Detected IProxy[$iproxyType] variable")
            
            // Group 1: Find @injected Functions
            val injectedFunctionsGroup = DefaultActionGroup("Find @injected Functions", true)
            injectedFunctionsGroup.isPopup = true
            
            // Query for matching @injected functions
            val matchingFunctions = findInjectedFunctions(project, iproxyType)
            
            if (matchingFunctions.isNotEmpty()) {
                println("[IProxy Debug] Found ${matchingFunctions.size} matching functions for type: $iproxyType")
                matchingFunctions.forEach { function ->
                    // Clean up module path - remove file path prefix and extension
                    val cleanModule = function.module
                        .replace("/Users/s22625/repos/sge-hub/src/", "")
                        .replace(".Users.s22625.repos.sge-hub.src.", "")
                        .replace("/", ".")
                        .removeSuffix(".py")
                        .removeSuffix("." + function.name)
                    
                    println("[IProxy Debug] - Function: ${function.name} in ${cleanModule}")
                    // Try different approach: disable mnemonic entirely
                    val action = object : AnAction() {
                        init {
                            // Set the template presentation without mnemonic
                            templatePresentation.setText(function.name, false)
                            templatePresentation.description = cleanModule
                        }
                        
                        override fun actionPerformed(e: AnActionEvent) {
                            element?.let {
                                runPinjectedCall(project, function, name, it)
                            }
                        }
                        
                        override fun update(e: AnActionEvent) {
                            super.update(e)
                            // Ensure text is set without mnemonic processing
                            e.presentation.setText(function.name, false)
                        }
                    }
                    injectedFunctionsGroup.add(action)
                }
            } else {
                println("[IProxy Debug] No matching functions found for type: $iproxyType")
                injectedFunctionsGroup.add(object : AnAction(
                    "No matching functions found",
                    "No @injected functions accept $iproxyType",
                    null
                ) {
                    override fun actionPerformed(e: AnActionEvent) {
                        // No-op
                    }
                    
                    override fun update(e: AnActionEvent) {
                        e.presentation.isEnabled = false
                    }
                })
            }
            
            // Add refresh option
            injectedFunctionsGroup.addSeparator()
            injectedFunctionsGroup.add(object : AnAction(
                "Refresh Function List",
                "Re-index @injected functions (run pinjected-indexer update)",
                null
            ) {
                override fun actionPerformed(e: AnActionEvent) {
                    refreshIndexer(project)
                }
            })
            
            mainGroup.add(injectedFunctionsGroup)
            mainGroup.addSeparator()
        }
        
        // Group 2: Run Configurations
        val configurationsGroup = DefaultActionGroup("Run Configurations", true)
        configurationsGroup.isPopup = true
        
        // Get existing configurations
        val helper = InjectedFunctionActionHelperObject.createSafely(project)
        if (helper != null) {
            try {
                val configs = helper.cachedConfigurations(name).blockingGet(5000) ?: emptyList()
                
                if (configs.isNotEmpty()) {
                    configs.forEach { config ->
                        configurationsGroup.add(object : AnAction(
                            config.name,
                            "Run ${config.script_path}",
                            null
                        ) {
                            override fun actionPerformed(e: AnActionEvent) {
                                helper.runInBackground("Running ${config.name}") { indicator ->
                                    indicator.fraction = 0.1
                                    helper.runConfig(config)
                                    indicator.fraction = 1.0
                                }
                            }
                        })
                    }
                } else {
                    configurationsGroup.add(object : AnAction(
                        "No configurations found",
                        "Click 'Update Configurations' to refresh",
                        null
                    ) {
                        override fun actionPerformed(e: AnActionEvent) {
                            // No-op
                        }
                        
                        override fun update(e: AnActionEvent) {
                            e.presentation.isEnabled = false
                        }
                    })
                }
                
                configurationsGroup.addSeparator()
                configurationsGroup.add(object : AnAction(
                    "Update Configurations",
                    "Refresh configuration cache",
                    null
                ) {
                    override fun actionPerformed(e: AnActionEvent) {
                        helper.runInBackground("Updating configurations") { indicator ->
                            helper.updateConfigurations()
                        }
                    }
                })
                
            } catch (e: Exception) {
                LOG.error("Error loading configurations", e)
            }
        }
        
        mainGroup.add(configurationsGroup)
        
        // Group 3: Utilities
        val utilitiesGroup = DefaultActionGroup("Utilities", true)
        utilitiesGroup.isPopup = true
        
        utilitiesGroup.add(object : AnAction(
            "Copy Variable Name",
            "Copy '$name' to clipboard",
            null
        ) {
            override fun actionPerformed(e: AnActionEvent) {
                val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
                val selection = java.awt.datatransfer.StringSelection(name)
                clipboard.setContents(selection, selection)
                
                NotificationGroupManager.getInstance()
                    .getNotificationGroup("Pinjected Plugin")
                    .createNotification(
                        "Copied to Clipboard",
                        "'$name' copied to clipboard",
                        NotificationType.INFORMATION
                    )
                    .notify(project)
            }
        })
        
        if (iproxyType != null) {
            utilitiesGroup.add(object : AnAction(
                "Copy Type Parameter",
                "Copy '$iproxyType' to clipboard",
                null
            ) {
                override fun actionPerformed(e: AnActionEvent) {
                    val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
                    val selection = java.awt.datatransfer.StringSelection(iproxyType)
                    clipboard.setContents(selection, selection)
                    
                    NotificationGroupManager.getInstance()
                        .getNotificationGroup("Pinjected Plugin")
                        .createNotification(
                            "Copied to Clipboard",
                            "'$iproxyType' copied to clipboard",
                            NotificationType.INFORMATION
                        )
                        .notify(project)
                }
            })
            
            utilitiesGroup.add(object : AnAction(
                "Generate pinjected call",
                "Generate command to call function",
                null
            ) {
                override fun actionPerformed(e: AnActionEvent) {
                    val module = element?.containingFile?.name?.removeSuffix(".py") ?: "module"
                    val command = "pinjected call <function_module> $module.$name"
                    
                    val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
                    val selection = java.awt.datatransfer.StringSelection(command)
                    clipboard.setContents(selection, selection)
                    
                    NotificationGroupManager.getInstance()
                        .getNotificationGroup("Pinjected Plugin")
                        .createNotification(
                            "Command Template Copied",
                            "Replace <function_module> with the target function's module path",
                            NotificationType.INFORMATION
                        )
                        .notify(project)
                }
            })
        }
        
        utilitiesGroup.add(object : AnAction(
            "Visualize Dependency Graph",
            "Run HTML dependency graph visualization for this target",
            null
        ) {
            override fun actionPerformed(e: AnActionEvent) {
                val helper = InjectedFunctionActionHelperObject.createSafely(project)
                if (helper != null) {
                    helper.runInBackground("Visualizing dependency graph for $name") { indicator ->
                        indicator.text = "Looking for $name in the script"
                        indicator.fraction = 0.1
                        
                        try {
                            helper.cachedConfigurations(name).blockingGet(30000)!!.firstOrNull {
                                it.name.endsWith("_viz")
                            }?.let { vizConfig ->
                                indicator.text = "Running visualization for ${vizConfig.name}"
                                indicator.fraction = 0.9
                                helper.runConfig(vizConfig)
                                indicator.fraction = 1.0
                            } ?: throw Exception("No visualization config found for $name")
                        } catch (ex: Exception) {
                            ApplicationManager.getApplication().invokeLater {
                                NotificationGroupManager.getInstance()
                                    .getNotificationGroup("Pinjected Plugin")
                                    .createNotification(
                                        "Visualization Failed",
                                        "Failed to visualize dependency graph for $name: ${ex.message}",
                                        NotificationType.ERROR
                                    )
                                    .notify(project)
                            }
                        }
                    }
                } else {
                    NotificationGroupManager.getInstance()
                        .getNotificationGroup("Pinjected Plugin")
                        .createNotification(
                            "Python Not Configured",
                            "Please configure Python interpreter for this project",
                            NotificationType.ERROR
                        )
                        .notify(project)
                }
            }
        })
        
        utilitiesGroup.addSeparator()
        utilitiesGroup.add(object : AnAction(
            "Run Diagnostics",
            "Check plugin configuration",
            null
        ) {
            override fun actionPerformed(e: AnActionEvent) {
                DiagnosticRunner.runDiagnostics(project)
            }
        })
        
        mainGroup.add(utilitiesGroup)
        
        // Create and show the popup
        val dataContext = SimpleDataContext.builder()
            .add(CommonDataKeys.PROJECT, project)
            .build()
        
        val popup = JBPopupFactory.getInstance()
            .createActionGroupPopup(
                "Pinjected Actions - $name",
                mainGroup,
                dataContext,
                JBPopupFactory.ActionSelectionAid.SPEEDSEARCH,
                true
            )
        
        if (e != null) {
            popup.show(com.intellij.ui.awt.RelativePoint(e))
        } else {
            popup.showInFocusCenter()
        }
    }
    
    /**
     * Extract IProxy type parameter from element.
     */
    private fun extractIProxyType(element: PsiElement?): String? {
        if (element == null) return null
        
        val targetExpression = PsiTreeUtil.getParentOfType(element, PyTargetExpression::class.java)
        return extractIProxyTypeFromTargetExpression(targetExpression)
    }
    
    /**
     * Extract IProxy type from a PyTargetExpression.
     */
    private fun extractIProxyTypeFromTargetExpression(targetExpression: PyTargetExpression?): String? {
        if (targetExpression == null) {
            println("[IProxy Debug] extractIProxyType: targetExpression is null")
            return null
        }
        
        val annotation = targetExpression.annotation
        println("[IProxy Debug] Target expression annotation class: ${annotation?.javaClass?.simpleName}")
        println("[IProxy Debug] Annotation text: ${annotation?.text}")
        LOG.debug("Target expression annotation: ${annotation?.javaClass?.simpleName}")
        LOG.debug("Annotation text: ${annotation?.text}")
        
        if (annotation == null) {
            println("[IProxy Debug] No annotation found, checking assigned value...")
            // Sometimes the type might be inferred, check the assigned value
            val assignedValue = targetExpression.findAssignedValue()
            println("[IProxy Debug] Assigned value: ${assignedValue?.text}")
            LOG.debug("Assigned value: ${assignedValue?.text}")
            
            // Check if assigned value is an IProxy call
            if (assignedValue?.text?.contains("IProxy") == true) {
                println("[IProxy Debug] Found IProxy in assigned value, returning 'Unknown'")
                // Try to extract from the variable name pattern (e.g., test_proxy might be IProxy[int])
                // This is a fallback - normally we should have the annotation
                return "Unknown"
            }
            return null
        }
        
        // Handle PyAnnotationImpl wrapper (PyCharm PSI structure)
        val actualAnnotation = if (annotation is PyAnnotation) {
            println("[IProxy Debug] Found PyAnnotation wrapper, extracting value...")
            val value = annotation.value
            println("[IProxy Debug] Extracted value class: ${value?.javaClass?.simpleName}")
            println("[IProxy Debug] Extracted value text: ${value?.text}")
            value
        } else {
            println("[IProxy Debug] Direct annotation (not wrapped)")
            annotation
        }
        
        // Check if it's IProxy[T]
        if (actualAnnotation is PySubscriptionExpression) {
            val operand = actualAnnotation.operand
            println("[IProxy Debug] Subscription operand class: ${operand?.javaClass?.simpleName}")
            println("[IProxy Debug] Subscription operand text: ${operand?.text}")
            LOG.debug("Subscription operand: ${operand?.text}")
            
            if (operand is PyReferenceExpression && operand.name == "IProxy") {
                val typeParam = actualAnnotation.indexExpression?.text
                println("[IProxy Debug] Found IProxy type parameter: $typeParam")
                LOG.debug("Found IProxy type parameter: $typeParam")
                return typeParam
            } else {
                println("[IProxy Debug] Operand is not IProxy, name=${(operand as? PyReferenceExpression)?.name}")
            }
        } else {
            println("[IProxy Debug] Actual annotation is not PySubscriptionExpression, it's ${actualAnnotation?.javaClass?.simpleName}")
        }
        
        // Check for simple IProxy without parameters
        if (actualAnnotation is PyReferenceExpression) {
            val refExpr = actualAnnotation
            println("[IProxy Debug] Checking PyReferenceExpression, name=${refExpr.name}")
            if (refExpr.name == "IProxy") {
                println("[IProxy Debug] Found simple IProxy without type parameter")
                LOG.debug("Found simple IProxy without type parameter")
                return "Any"
            }
        }
        
        println("[IProxy Debug] No IProxy type found, returning null")
        return null
    }
    
    /**
     * Query indexer for @injected functions matching the type.
     */
    private fun findInjectedFunctions(project: Project, typeName: String): List<FunctionInfo> {
        return try {
            // Auto-refresh indexer before querying (quick update)
            println("[IProxy Debug] Auto-refreshing indexer before query...")
            val projectRoot = project.basePath ?: "."
            val updateCommand = listOf("pinjected-indexer", "--root", projectRoot, "update", "--quick")
            
            try {
                val updateProcess = ProcessBuilder(updateCommand)
                    .directory(java.io.File(projectRoot))
                    .start()
                    
                // Capture output for debugging
                val stdout = updateProcess.inputStream.bufferedReader().use { it.readText() }
                val stderr = updateProcess.errorStream.bufferedReader().use { it.readText() }
                
                val completed = updateProcess.waitFor(10, java.util.concurrent.TimeUnit.SECONDS)
                
                if (stdout.isNotEmpty()) {
                    println("[IProxy Debug] Auto-refresh stdout:\n$stdout")
                }
                if (stderr.isNotEmpty()) {
                    println("[IProxy Debug] Auto-refresh stderr:\n$stderr")
                }
                
                if (completed && updateProcess.exitValue() == 0) {
                    println("[IProxy Debug] Indexer auto-refresh completed successfully")
                } else {
                    println("[IProxy Debug] Indexer auto-refresh failed with exit code: ${updateProcess.exitValue()}")
                }
            } catch (e: Exception) {
                println("[IProxy Debug] Auto-refresh failed (non-critical): ${e.message}")
            }
            
            println("[IProxy Debug] Querying pinjected-indexer for type: $typeName")
            val functions = IProxyActionUtil.queryInjectedFunctions(project, typeName).get()
            println("[IProxy Debug] Raw function data from indexer:")
            functions.forEach { func ->
                println("[IProxy Debug]   - Name: '${func.function_name}', Module: '${func.module_path}'")
            }
            functions.map { func ->
                FunctionInfo(
                    name = func.function_name,
                    module = func.module_path,
                    filePath = func.file_path,
                    lineNumber = func.line_number,
                    docstring = func.docstring
                )
            }
        } catch (e: Exception) {
            LOG.error("Error querying injected functions", e)
            println("[IProxy Debug] Error querying functions: ${e.message}")
            emptyList()
        }
    }
    
    /**
     * Refresh the pinjected-indexer database.
     */
    private fun refreshIndexer(project: Project) {
        println("[IProxy Debug] Refreshing pinjected-indexer...")
        try {
            val projectRoot = project.basePath ?: "."
            val command = listOf("pinjected-indexer", "--root", projectRoot, "update")
            
            println("[IProxy Debug] Running command: ${command.joinToString(" ")}")
            
            val processBuilder = ProcessBuilder(command)
            processBuilder.directory(java.io.File(projectRoot))
            
            val process = processBuilder.start()
            
            // Capture stdout
            val stdout = process.inputStream.bufferedReader().use { it.readText() }
            val stderr = process.errorStream.bufferedReader().use { it.readText() }
            
            val exitCode = process.waitFor(30, java.util.concurrent.TimeUnit.SECONDS)
            
            if (stdout.isNotEmpty()) {
                println("[IProxy Debug] Indexer stdout:\n$stdout")
            }
            if (stderr.isNotEmpty()) {
                println("[IProxy Debug] Indexer stderr:\n$stderr")
            }
            
            if (exitCode && process.exitValue() == 0) {
                println("[IProxy Debug] Indexer refreshed successfully")
                NotificationGroupManager.getInstance()
                    .getNotificationGroup("Pinjected Plugin")
                    .createNotification(
                        "Indexer Refreshed",
                        "Successfully updated pinjected-indexer database",
                        NotificationType.INFORMATION
                    )
                    .notify(project)
            } else {
                println("[IProxy Debug] Indexer refresh failed or timed out")
                NotificationGroupManager.getInstance()
                    .getNotificationGroup("Pinjected Plugin")
                    .createNotification(
                        "Indexer Refresh Failed",
                        "Failed to update pinjected-indexer database",
                        NotificationType.ERROR
                    )
                    .notify(project)
            }
        } catch (e: Exception) {
            LOG.error("Error refreshing indexer", e)
            println("[IProxy Debug] Exception refreshing indexer: ${e.message}")
        }
    }
    
    /**
     * Run pinjected call command with the selected @injected function and IProxy variable.
     */
    private fun runPinjectedCall(project: Project, function: FunctionInfo, iproxyVarName: String, element: PsiElement) {
        // Get the IProxy variable's module path
        val projectBasePath = project.basePath ?: ""
        val containingFile = element.containingFile
        
        // Calculate IProxy module path from file path
        val iproxyModule = containingFile?.virtualFile?.path?.let { path ->
            // Try to extract module path relative to project
            var modulePath = path
            
            // Remove project base path
            if (projectBasePath.isNotEmpty() && modulePath.startsWith(projectBasePath)) {
                modulePath = modulePath.substring(projectBasePath.length + 1)
            }
            
            // Remove common source directories
            modulePath = modulePath
                .replace("src/", "")
                .replace("packages/", "")
                .replace("/", ".")
                .removeSuffix(".py")
            
            modulePath
        } ?: "unknown_module"
        
        // Clean up function module path
        val functionModule = function.module
            .split("/").last()  // Take only the module part, not the full path
            .replace("/", ".")
            .removeSuffix(".py")
            .removeSuffix("." + function.name)
        
        // Get the helper to run the configuration
        val helper = InjectedFunctionActionHelperObject.createSafely(project)
        if (helper == null) {
            NotificationGroupManager.getInstance()
                .getNotificationGroup("Pinjected Plugin")
                .createNotification(
                    "Python Not Configured",
                    "Please configure Python interpreter for this project",
                    NotificationType.ERROR
                )
                .notify(project)
            return
        }
        
        // Find the path to pinjected's __main__.py using the shared helper method
        val pinjectedMainPath = try {
            helper.findPinjectedMainPath()
        } catch (e: Exception) {
            LOG.error("Failed to find pinjected __main__.py path", e)
            NotificationGroupManager.getInstance()
                .getNotificationGroup("Pinjected Plugin")
                .createNotification(
                    "Configuration Error",
                    "Could not find pinjected module. Is it installed?",
                    NotificationType.ERROR
                )
                .notify(project)
            return
        }
        
        // Create PyConfiguration for pinjected call using the same pattern as existing runner
        val config = PyConfiguration(
            name = "pinjected call ${function.name} with $iproxyVarName",
            script_path = pinjectedMainPath,
            interpreter_path = helper.interpreterPath,
            arguments = listOf(
                "call",
                "${functionModule}.${function.name}",
                "${iproxyModule}.$iproxyVarName"
            ),
            working_dir = project.basePath ?: System.getProperty("user.dir")
        )
        
        println("[IProxy Debug] Running pinjected call:")
        println("[IProxy Debug]   Function: ${functionModule}.${function.name}")
        println("[IProxy Debug]   IProxy: ${iproxyModule}.$iproxyVarName")
        println("[IProxy Debug]   Working dir: ${config.working_dir}")
        
        // Run the configuration
        try {
            helper.runConfig(config)
            
            NotificationGroupManager.getInstance()
                .getNotificationGroup("Pinjected Plugin")
                .createNotification(
                    "Running pinjected call",
                    "Executing: ${function.name} with $iproxyVarName",
                    NotificationType.INFORMATION
                )
                .notify(project)
        } catch (e: Exception) {
            LOG.error("Failed to run pinjected call", e)
            NotificationGroupManager.getInstance()
                .getNotificationGroup("Pinjected Plugin")
                .createNotification(
                    "Failed to run",
                    "Error: ${e.message}",
                    NotificationType.ERROR
                )
                .notify(project)
        }
    }
    
    data class FunctionInfo(
        val name: String,
        val module: String,
        val filePath: String,
        val lineNumber: Int,
        val docstring: String?
    )
}
