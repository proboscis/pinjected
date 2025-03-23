package com.proboscis.kotlinopenai

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
import org.zeromq.SocketType
import org.zeromq.ZContext
import org.zeromq.ZMQ
import java.io.File
import javax.script.ScriptEngineManager
import kotlin.concurrent.thread

val InjectedFunctionMarkers = listOf("@injected_function", "@Injected.bind", "provide_", "@injected_instance", "@injected", "@instance")
val InjectedTypeMarkers = listOf("Injected", "DelegatedVar", "PartialInjectedFunction", "Designed") // I want to visualize the html with default design. how?
fun getInferredType(element: PsiElement): String? {
    // Get the PyExpression from the PsiElement
    val pyExpression = getParentOfType(element, PyExpression::class.java) ?: return null

    // Get the TypeEvalContext for the element
    val typeEvalContext = TypeEvalContext.userInitiated(element.project, element.containingFile)

    // Get the inferred type
    val inferredType: PyType? = typeEvalContext.getType(pyExpression)

    // Return the type as a String, or null if the type could not be inferred
    return inferredType?.name
}

fun getTargetName(element: PsiElement): String? {
    if (getParentOfType(element, PyClass::class.java) != null) {
        return null
    }

    val pyVarDef = getParentOfType(element, PyTargetExpression::class.java)
    val typeName = getInferredType(element)
    //println("inferred type for $element / $pyVarDef: ${typeName}")
    pyVarDef?.let {
        if (InjectedTypeMarkers.any() { typeName?.contains(it) == true }) {
            return pyVarDef.name
        }
    }
    val pyFunction = getParentOfType(element, PyFunction::class.java) ?: return null
    // If the PyTargetExpression also has the same PyFunction ancestor, it means it's in the function body.
    if (pyVarDef != null && PsiTreeUtil.getParentOfType(pyVarDef, PyFunction::class.java) == pyFunction) {
        return null
    }


    // this includes a case of defining a var in a class
    val containsMarker = InjectedFunctionMarkers.any { pyFunction.text.contains(it) }
    if (pyFunction.nameIdentifier == element && containsMarker) {
        return pyFunction.name
    }
    return null
}


fun createActions(project: Project, name: String): List<ActionItem> {
    // get current file
    // find the cached design paths
    // you can inspect the configurations to find the design paths
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
    val show = ActionItem("Show $name (if no design, uses __default_design_path__)") {
        helper.runInBackground("visualizing ${name}") { indicator ->
            indicator.fraction = 0.1
            indicator.text = "Looking for ${name} in the script"

            helper.cachedConfigurations(name).blockingGet(30000)!!.firstOrNull {
                it.name.endsWith("_viz")
            }.let { helper.runConfig(it ?: throw Exception("No config found for $(name)")) }
            indicator.fraction = 1.0
        }
    }
    // TODO add a 'scripted' action that runs the script and then runs the function
    val script = ActionItem("Python Actions") {
        helper.runInBackground("Running ${name}") { indicator ->
            // 0. get MyPluginService instance
            // 1. run a script to fetch available actions
            // 2. show a popup with the actions
            // 3. run the action implemented in python, by passing a proxy server's address
            val service = project.getService(MyPluginService::class.java)
            val zmqAddr = service?.zmqServer?.address
            val res = helper.runPython(
                    "-m pinjected.run_config_utils run_with_kotlin --kotlin-zmq-address $zmqAddr".split(" ")
            )
            // the action needs to be run on this thread though...
            println(res)
        }
    }
    val makeSandbox = ActionItem("Make Sandbox") {
        helper.runInBackground("Making Sandbox") { indicator ->
            // 1. get module path of both the subject and the design.
            indicator.fraction = 0.1
            indicator.text = "looking for ${name} in the script"
            // 2. create a sandbox file with the module path at {{module_path}}_sandbox_{{time}}.py
            val filePath = helper.getFilePath()
            val sandboxPath = helper.runPython(
                    "-m pinjected.run_config_utils make_sandbox ${filePath} ${name}".split(" ")
            ).trim()
            // 3. open the sandbox file in the editor.
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
                val configs: List<PyConfiguration> = helper.configurations()[name]!!
                // popup with conf.name and let the user select a conf to run.
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
        val updateCompletionCache = ActionItem("update completion cache") {
            InjectedCompletions.updateCache(project, helper.getFilePath()!!)
        }
        return listOf(run, show, makeSandbox, selectAction) + cachedRuns + listOf(updateConfigCache, updateCompletionCache)
    } catch (e: Exception) {
        helper.showNotification("Error", "Could not get python configs: ${e.message}\n${e.stackTraceToString()}")
        throw e
    }
}


class ZmqServer(private val port: Int, private val onMessageReceived: (String) -> String) {
    private lateinit var zmqContext: ZContext
    private lateinit var zmqSocket: ZMQ.Socket
    val address = "tcp://localhost:$port"

    fun start() {
        zmqContext = ZContext()
        zmqSocket = zmqContext.createSocket(SocketType.REP).apply {
            bind(address)
        }

        thread(start = true) {
            while (!Thread.currentThread().isInterrupted) {
                val message = zmqSocket.recvStr()
                val response = onMessageReceived(message)
                zmqSocket.send(response)
            }
        }
    }

    fun stop() {
        zmqSocket.close()
        zmqContext.close()
    }
}

class AnnotatedFunctionGutterIconProvider : LineMarkerProvider {
    override fun getLineMarkerInfo(element: PsiElement): LineMarkerInfo<*>? {
        val icon = AllIcons.Actions.Execute
        // So this is called only once the page is loaded?
        // I want to cache the result of inspection of this file.
        // I mean to have options of designs
        return getTargetName(element)?.let {
            return createMarker(
                    element,
                    icon,
                    "Run Injected Object",
                    GutterIconRenderer.Alignment.CENTER
            ) { ->
                // so now actions are created upon clicking.
                // we can use cached results to create actions.
                // the problem is that it takes some time to run the python code for inspection.
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
    val log = Logger.getInstance("com.proboscis.kotlinopenai.showPopupChooser")
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

@Service
class MyPluginService {
    val zmqServer: ZmqServer

    init {
        val port = 5555 // Change to the desired port number
        zmqServer = ZmqServer(port) { message ->
            try {
                val result = evaluateKotlinCode(message)
                "Success: $result"
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
        }
        zmqServer.start()
    }

    private fun evaluateKotlinCode(code: String): Any? {
        val scriptEngine =
                ScriptEngineManager().getEngineByExtension("kts") ?: throw Exception("Kotlin script engine not found")
        return scriptEngine.eval(code)
    }

    // Add a dispose method to stop the server when the plugin is disposed or disabled
    fun dispose() {
        zmqServer.stop()
    }
}