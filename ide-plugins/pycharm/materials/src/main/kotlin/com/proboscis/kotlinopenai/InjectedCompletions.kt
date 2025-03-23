package com.proboscis.kotlinopenai

import com.google.common.cache.CacheBuilder
import com.intellij.codeInsight.completion.*
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.icons.AllIcons
import com.intellij.notification.NotificationType
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.project.Project
import com.intellij.patterns.PlatformPatterns
import com.intellij.psi.PsiElement
import com.intellij.util.ProcessingContext
import kotlinx.serialization.Serializable
import okhttp3.internal.notifyAll
import java.io.File
import java.nio.file.Files
import java.nio.file.Paths
import java.util.concurrent.TimeUnit

@Serializable
data class CustomCompletion(
        val name: String,
        val description: String,
        val tail: String,
)
@Serializable
data class BindingLocation(
        val type:String,
        val value:String

){
    fun toPsiElement(project: Project): PsiElement? {
        return when (type) {
            "path" -> InjectedGotoDeclaration.resolveStringToPsiElement(project,value)
            "coordinates" -> {
                val (file,lineno,colno) = value.split(":")
                InjectedGotoDeclaration.navigateToFileOffset(project,file,lineno.toInt(),colno.toInt())
            }
            else -> null
        }
    }
}
@Serializable
data class DesignMetadata(
        val key: String,
        val location: BindingLocation
)

object InjectedCompletions {
    var update_running = false
    val cache = CacheBuilder.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(10, TimeUnit.MINUTES)
            .build<String, List<LookupElementBuilder>>()

    fun isPythonFileWithMetaDesign(filePath: String): Boolean {
        val path = Paths.get(filePath)
        if (!Files.exists(path) || !Files.isRegularFile(path)) {
            println("The file path either does not exist or it is not a regular file.")
            return false
        }

        if (!filePath.endsWith(".py")) {
            println("The file is not a Python file.")
            return false
        }

        val fileLines = Files.readAllLines(path)
        for (line in fileLines) {
            if (line.contains("__meta_design__")) {
                return true
            }
        }

        return false
    }

    fun updateCache(project: Project, filePath: String) {
        update_running = true
        val helper = InjectedFunctionActionHelper(project)
        helper.runInBackground("Updating injected completions for $filePath") { indicator ->
            try {
                indicator.fraction = 0.1
                cache.invalidate(filePath)
                indicator.fraction = 0.3
                cache[filePath, {
                    // check if the text in file contains "__meta_design__"
                    if (isPythonFileWithMetaDesign(filePath)) {
                        val completions = helper.listCompletions(filePath)
                        buildElements(completions)
                    } else {
                       // If this happens, i want to forget about this
                        throw Exception("The file does not contain __meta_design__")
                    }
                }]
            } catch (e: Exception) {
                if (e.message?.contains("The file does not contain __meta_design__") == true) {
                    // do nothing
                } else {
                    helper.showNotification("Error while updating injected completions", e.message
                            ?: "Unknown error", NotificationType.INFORMATION)
                }
            } finally {
                indicator.fraction = 1.0
                update_running = false
            }
        }
    }

    fun buildElements(completions: List<CustomCompletion>): List<LookupElementBuilder> {
        val elements = mutableListOf<LookupElementBuilder>()
        for (item in completions) {
            elements.add(
                    LookupElementBuilder
                            .create(item.name)
                            .withIcon(AllIcons.General.InheritedMethod)
                            .withTypeText(item.description)
                            .withTailText(item.tail)
            )
        }
        return elements
    }
}

class BackgroundCache<T>(project: Project, impl: (String) -> T) {
    val cache = CacheBuilder.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(5, TimeUnit.MINUTES)
            .build<String, T>()
    val helper: InjectedFunctionActionHelper = InjectedFunctionActionHelper(project)
    val impl = impl
    var update_running = false

    fun getOrUpdate(key: String): T? {
        if (cache.getIfPresent(key) == null) {
            update(key)
        }
        return cache.getIfPresent(key)
    }

    fun update(key: String) {
        if (update_running) {
            return
        }
        update_running = true
        helper.runInBackground("Updating injected metadata for $key") { indicator ->
            try {
                indicator.fraction = 0.1
                cache.invalidate(key)
                indicator.fraction = 0.3
                cache[key, { impl(key) }]
            } catch (e: Exception) {
                helper.showNotification("Error while updating injected completions", e.message
                        ?: "Unknown error", NotificationType.INFORMATION)
            } finally {
                indicator.fraction = 1.0
                update_running = false
            }
        }
    }
}

@Serializable
data class PinjectedDeclaration(
        val name: String,
        val module: String,
)

object PinjectedCaches {
    val declarationsCache = CacheBuilder.newBuilder()
            .build<Project, BackgroundCache<List<PinjectedDeclaration>>>()

    fun getDeclarationsCache(project: Project): BackgroundCache<List<PinjectedDeclaration>> {
        return declarationsCache[project, {
            BackgroundCache(project) { filePath ->
                val helper = InjectedFunctionActionHelper(project)
                //helper.listDeclarations(filePath)
                /**
                 * How do we make PsiElement from a module path and a name?
                 *
                 */
                listOf()
            }
        }]
    }

}

class InjectedCompletionProvider : CompletionProvider<CompletionParameters>() {

    override fun addCompletions(
            parameters: CompletionParameters,
            context: ProcessingContext,
            result: CompletionResultSet
    ) {
        val editor: Editor = parameters.editor
        editor.getProject()?.let { project ->
            val fileEditorManager = FileEditorManager.getInstance(project)
            val currentFile = fileEditorManager.selectedFiles[0] // Caution: might throw an exception if no files are selected
            if (currentFile != null) {
                val filePath = currentFile.path
                if (File(filePath).exists()) {
                    val list = InjectedCompletions.cache.getIfPresent(filePath)
                    for (item in list ?: listOf()) {
                        result.addElement(item)
                    }
                    if (list == null && !InjectedCompletions.update_running) {
                        InjectedCompletions.updateCache(project, filePath)
                    }
                }
            }
        }
    }
}

class InjectedCompletionContributor : CompletionContributor() {
    init {
        extend(
                CompletionType.BASIC,
                PlatformPatterns.psiElement(),
                InjectedCompletionProvider()
        )

    }
}