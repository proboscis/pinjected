package com.proboscis.pinjectdesign.kotlin.completion

import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.data.CustomCompletion
import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionProvider
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.completion.CompletionType
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.icons.AllIcons
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.project.Project
import com.intellij.patterns.PlatformPatterns
import com.intellij.util.ProcessingContext
import java.io.File
import java.nio.file.Files
import java.nio.file.Paths
import java.util.concurrent.ConcurrentHashMap

object InjectedCompletions {
    private val cache = ConcurrentHashMap<String, List<LookupElementBuilder>>()
    @Volatile var isUpdateRunning = false
        private set

    fun isPythonFileWithInjection(filePath: String): Boolean {
        val path = Paths.get(filePath)
        if (!Files.exists(path) || !Files.isRegularFile(path)) {
            return false
        }

        if (!filePath.endsWith(".py")) {
            return false
        }

        val fileLines = Files.readAllLines(path)
        for (line in fileLines) {
            if (line.contains("__meta_design__") || line.contains("__design__")) {
                return true
            }
        }

        return false
    }

    fun updateCache(project: Project, filePath: String) {
        if (isUpdateRunning) return
        isUpdateRunning = true
        
        val helper = InjectedFunctionActionHelper(project)
        helper.runInBackground("Updating injected completions for $filePath") { indicator ->
            try {
                indicator.fraction = 0.1
                cache.remove(filePath)
                indicator.fraction = 0.3
                
                if (isPythonFileWithInjection(filePath)) {
                    val completions = helper.listCompletions(filePath)
                    cache[filePath] = buildElements(completions)
                } else {
                    // File doesn't contain injection points
                }
            } catch (e: Exception) {
                val message = e.message
                if (message == null || !message.contains("The file does not contain __meta_design__")) {
                    helper.showNotification("Error while updating injected completions", 
                        e.message ?: "Unknown error")
                }
            } finally {
                indicator.fraction = 1.0
                isUpdateRunning = false
            }
        }
    }

    fun buildElements(completions: List<CustomCompletion>): List<LookupElementBuilder> {
        return completions.map { item ->
            LookupElementBuilder
                .create(item.name)
                .withIcon(AllIcons.General.InheritedMethod)
                .withTypeText(item.description)
                .withTailText(item.tail)
        }
    }
    
    fun getCachedCompletions(filePath: String): List<LookupElementBuilder>? {
        return cache[filePath]
    }
}

class InjectedCompletionProvider : CompletionProvider<CompletionParameters>() {
    override fun addCompletions(
        parameters: CompletionParameters,
        context: ProcessingContext,
        result: CompletionResultSet
    ) {
        val editor: Editor = parameters.editor
        editor.project?.let { project ->
            val fileEditorManager = FileEditorManager.getInstance(project)
            val currentFile = fileEditorManager.selectedFiles.firstOrNull() ?: return
            
            val filePath = currentFile.path
            if (File(filePath).exists()) {
                val cachedCompletions = InjectedCompletions.getCachedCompletions(filePath)
                
                cachedCompletions?.forEach { item ->
                    result.addElement(item)
                }
                
                if (cachedCompletions == null && !InjectedCompletions.isUpdateRunning) {
                    InjectedCompletions.updateCache(project, filePath)
                }
            }
        }
    }
}

class InjectedFunctionCompletionContributor : CompletionContributor() {
    init {
        extend(
            CompletionType.BASIC,
            PlatformPatterns.psiElement(),
            InjectedCompletionProvider()
        )
    }
}
