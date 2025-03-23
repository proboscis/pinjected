package com.proboscis.kotlinopenai

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowAnchor
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.content.ContentFactory
import com.intellij.openapi.project.Project
import javax.swing.JTree
import javax.swing.tree.DefaultMutableTreeNode
import javax.swing.tree.DefaultTreeModel
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleManager
import com.intellij.openapi.roots.ModuleRootManager
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiManager
import com.intellij.psi.PsiRecursiveElementVisitor
import com.intellij.psi.search.FileTypeIndex
import com.intellij.psi.search.GlobalSearchScope
import com.intellij.psi.search.GlobalSearchScopes
import com.jetbrains.python.PythonFileType

class InjectedFunctionsToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val actionItemsTree = ActionItemsTree(project)

        val contentFactory = ContentFactory.SERVICE.getInstance()
        val content = contentFactory.createContent(actionItemsTree, "", false)
        toolWindow.contentManager.addContent(content)
    }
}

class ActionItemsTree(project: Project) : JTree() {
    init {
        val root = iterateModulesAndBuildTree(project)
        val mutableRoot = convertToMutableTreeNode(root)
        val treeModel = DefaultTreeModel(mutableRoot)
        model = treeModel
    }
}


fun processModuleSourceCode(module: Module): TreeNode {
    println("Processing module: ${module.name}")
    val moduleRootManager = ModuleRootManager.getInstance(module)
    val contentRoots = moduleRootManager.contentRoots
    val psiManager = PsiManager.getInstance(module.project)

    val moduleNode = TreeNode(module.name)

    val checkedDirectories = mutableSetOf<String>()

    for (contentRoot in contentRoots) {
        val directory = psiManager.findDirectory(contentRoot) ?: continue
        if (checkedDirectories.contains(directory.name)){
            continue
        }
        val virtualFiles = FileTypeIndex.getFiles(PythonFileType.INSTANCE, GlobalSearchScopes.directoryScope(directory, true))
        println("Found ${virtualFiles.size} files in ${directory.name} directory")
        for (virtualFile in virtualFiles) {
            println("Processing file: ${virtualFile.name}")
            val psiFile = psiManager.findFile(virtualFile) ?: continue
            val fileNode = TreeNode(psiFile.name)
            moduleNode.addChild(fileNode)

            psiFile.accept(object : PsiRecursiveElementVisitor() {
                override fun visitElement(element: PsiElement) {
                    super.visitElement(element)
                    getTargetName(element)?.let { targetName ->
                        val elementNode = TreeNode(targetName)
                        println("Found target: $targetName")
                        fileNode.addChild(elementNode)
                    }
                }
            })
        }
        checkedDirectories.add(directory.name)
        println("Checked directories: $checkedDirectories")
    }

    return moduleNode
}
class TreeNode(val name: String) {
    val children = mutableListOf<TreeNode>()

    fun addChild(node: TreeNode) {
        children.add(node)
    }

    fun printTree(indent: String = "") {
        println("$indent- $name")
        children.forEach { it.printTree(indent + "  ") }
    }
}

fun iterateModulesAndBuildTree(project: Project):TreeNode {
    val moduleManager = ModuleManager.getInstance(project)
    val modules = moduleManager.modules
    val root = TreeNode("root")
    for (module in modules) {
        if (!module.name.contains("archpainter", ignoreCase = true)) {
            continue
        }
        val moduleNode = processModuleSourceCode(module)
        root.addChild(moduleNode)
    }
    return root
}

class PrintModuleStructureAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project
        if (project != null) {
            val tree = iterateModulesAndBuildTree(project)
            println(tree)
        }
    }
}
fun convertToMutableTreeNode(node: TreeNode): DefaultMutableTreeNode {
    val mutableNode = DefaultMutableTreeNode(node.name)
    for (child in node.children) {
        val mutableChild = convertToMutableTreeNode(child)
        mutableNode.add(mutableChild)
    }
    return mutableNode
}