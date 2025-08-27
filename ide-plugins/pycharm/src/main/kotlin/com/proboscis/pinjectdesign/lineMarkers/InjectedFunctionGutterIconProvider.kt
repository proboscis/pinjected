package com.proboscis.pinjectdesign.lineMarkers

import com.intellij.codeInsight.daemon.GutterIconNavigationHandler
import com.intellij.codeInsight.daemon.LineMarkerInfo
import com.intellij.codeInsight.daemon.LineMarkerProvider
import com.intellij.icons.AllIcons
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.editor.markup.GutterIconRenderer
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.popup.JBPopupFactory
import com.intellij.openapi.ui.popup.PopupChooserBuilder
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.psi.PsiElement
import com.intellij.psi.util.PsiTreeUtil
import com.intellij.psi.util.PsiTreeUtil.getParentOfType
import com.intellij.ui.awt.RelativePoint
import com.intellij.ui.components.JBList
import com.jetbrains.python.psi.PyClass
import com.jetbrains.python.psi.PyExpression
import com.jetbrains.python.psi.PyFunction
import com.jetbrains.python.psi.PyTargetExpression
import com.jetbrains.python.psi.types.PyType
import com.jetbrains.python.psi.types.TypeEvalContext
import java.awt.event.MouseEvent
import javax.swing.DefaultListModel
import javax.swing.Icon
import java.io.File
import kotlin.concurrent.thread
import com.proboscis.pinjectdesign.helpers.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.config.saveModifiedDocuments
import com.proboscis.pinjectdesign.config.InjectedFunctionActionHelperObject

val InjectedFunctionMarkers = listOf("@injected_function", "@Injected.bind", "provide_", "@injected_instance", "@injected", "@instance")
val InjectedTypeMarkers = listOf("Injected", "DelegatedVar", "PartialInjectedFunction", "Designed")

fun getInferredType(element: PsiElement): String? {
    val pyExpression = getParentOfType(element, PyExpression::class.java) ?: return null
    val typeEvalContext = TypeEvalContext.userInitiated(element.project, element.containingFile)
    val inferredType: PyType? = typeEvalContext.getType(pyExpression)
    return inferredType?.name
}

fun getTargetName(element: PsiElement): String? {
    if (getParentOfType(element, PyClass::class.java) != null) {
        return null
    }

    val pyVarDef = getParentOfType(element, PyTargetExpression::class.java)
    val typeName = getInferredType(element)
    pyVarDef?.let {
        if (InjectedTypeMarkers.any() { typeName?.contains(it) == true }) {
            return pyVarDef.name
        }
    }
    val pyFunction = getParentOfType(element, PyFunction::class.java) ?: return null
    if (pyVarDef != null && PsiTreeUtil.getParentOfType(pyVarDef, PyFunction::class.java) == pyFunction) {
        return null
    }

    val containsMarker = InjectedFunctionMarkers.any { pyFunction.text.contains(it) }
    if (pyFunction.nameIdentifier == element && containsMarker) {
        return pyFunction.name
    }
    return null
}

fun createActions(project: Project, name: String): List<ActionItem> {
    val helper = InjectedFunctionActionHelper(project)
    val run = ActionItem("Run ${name} (if no design, uses __default_design_path__)") {
        helper.runInBackground("Running ${name}") { indicator ->
            indicator.fraction = 0.1
            helper.cachedConfigurations(name).blockingGet(30000)!!.first().let {
                indicator.text = "Running ${it.name}"
                helper.runConfig(it)
            }
            indicator.fraction = 1.0
        }
    }
    val show = ActionItem("Visualize Dependency Graph") {
        helper.runInBackground("visualizing ${name}") { indicator ->
            indicator.fraction = 0.1
            indicator.text = "Looking for ${name} in the script"

            helper.cachedConfigurations(name).blockingGet(30000)!!.firstOrNull {
                it.name.endsWith("_viz")
            }.let { helper.runConfig(it ?: throw Exception("No config found for ${name}")) }
            indicator.fraction = 1.0
        }
    }
    val makeSandbox = ActionItem("Make Sandbox") {
        helper.runInBackground("Making Sandbox") { indicator ->
            indicator.fraction = 0.1
            indicator.text = "looking for ${name} in the script"
            val filePath = helper.getFilePath()
            val sandboxPath = helper.runPython(
                    "-m pinjected.run_config_utils make_sandbox ${filePath} ${name}".split(" ")
            ).trim()
            indicator.fraction = 0.9
            indicator.text = "opening sandbox file"
            LocalFileSystem.getInstance().refreshIoFiles(listOf(File(sandboxPath)))
            val virtualFile = LocalFileSystem.getInstance().findFileByIoFile(File(sandboxPath))
                    ?: throw Exception("Could not find file $sandboxPath")
            ApplicationManager.getApplication().invokeLater {
                FileEditorManager.getInstance(project).openFile(virtualFile, true)
            }
            indicator.fraction = 1.0
            indicator.text = "done"
        }
    }
    val selectAction = ActionItem("select action") {
        helper.runInBackground("select action") { indicator ->
            ApplicationManager.getApplication().invokeLater {
                val configs = helper.configurations()[name]!!
                val popup = JBPopupFactory.getInstance().createPopupChooserBuilder(configs.map { it.name })
                        .setTitle("Select A Configuration to Run")
                        .setMovable(false)
                        .setResizable(false)
                        .setRequestFocus(true)
                        .setItemChosenCallback { selection ->
                            helper.runConfig(configs.associateBy { it.name }[selection]!!)
                        }
                        .createPopup()
                popup.showInFocusCenter()
            }
        }
    }
    try {
        val cachedRuns = helper.createRunActionsCached(name).blockingGet(30000)!!
        val updateConfigCache = ActionItem("update run configs") {
            helper.runInBackground("updating run configs") { indicator ->
                indicator.fraction = 0.1
                indicator.text = "Updating run config cache for ${name} in the script"
                helper.updateConfigurations()
                indicator.fraction = 1.0
            }
        }
        return listOf(run, show, makeSandbox, selectAction) + cachedRuns + listOf(updateConfigCache)
    } catch (e: Exception) {
        helper.showNotification("Error", "Could not get python configs: ${e.message}\n${e.stackTraceToString()}")
        throw e
    }
}

class InjectedFunctionGutterIconProvider : LineMarkerProvider {
    override fun getLineMarkerInfo(element: PsiElement): LineMarkerInfo<*>? {
        val icon = AllIcons.Actions.Execute
        return getTargetName(element)?.let {
            return createMarker(
                    element,
                    icon,
                    "Run Injected Object",
                    GutterIconRenderer.Alignment.CENTER
            ) { ->
                createActions(element.project, it)
            }
        }
    }
}

fun createMarker(
        element: PsiElement,
        icon: Icon,
        tip: String,
        alignment: GutterIconRenderer.Alignment,
        name: String,
        impl: (MouseEvent, PsiElement) -> Unit
): LineMarkerInfo<PsiElement> {
    val range = element.textRange
    return LineMarkerInfo(
            element,
            range,
            icon,
            { _ -> tip },
            CustomNavigationHandler(impl),
            alignment,
            { name }
    )
}

fun createMarker(
        element: PsiElement,
        icon: Icon,
        tip: String,
        alignment: GutterIconRenderer.Alignment,
        getActionItems: () -> List<ActionItem>
): LineMarkerInfo<PsiElement> {

    return createMarker(
            element,
            icon,
            tip,
            alignment,
            "Select Actions",
    ) { event, elem ->
        showPopupChooser(event, getActionItems())
    }
}

data class ActionItem(val name: String, val action: () -> Unit)

fun showPopupChooser(e: MouseEvent?, actionItems: List<ActionItem>) {
    val log = Logger.getInstance("com.cyberagent.ailab.pinjectdesign.showPopupChooser")
    log.warn("entering popup chooser")
    val listModel = DefaultListModel<String>()
    actionItems.map { it.name }.forEach { listModel.addElement(it) }
    val list = JBList(listModel)
    val builder = PopupChooserBuilder(list)

    builder.setTitle("Choose an Action")
    builder.setItemChoosenCallback {
        val index = list.selectedIndex
        log.warn("selected index: $index")
        val selectedItem = actionItems[index]
        log.warn("selected item: $selectedItem")
        selectedItem.action()
        log.warn("action executed")
    }

    val popup = builder.createPopup()
    log.warn("showing popup at $e")
    if (e != null) {
        popup.show(RelativePoint(e))
    } else {
        popup.showInFocusCenter()
    }
}

class CustomNavigationHandler(val impl: (MouseEvent, PsiElement) -> Unit) : GutterIconNavigationHandler<PsiElement> {
    override fun navigate(e: MouseEvent?, elt: PsiElement?) {
        saveModifiedDocuments()
        impl(e!!, elt!!)
    }
}
