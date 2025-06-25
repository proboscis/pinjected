package com.proboscis.pinjectdesign.kotlin.toolwindow

import com.intellij.icons.AllIcons
import com.intellij.openapi.actionSystem.*
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.FileEditorManagerEvent
import com.intellij.openapi.fileEditor.FileEditorManagerListener
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.ui.SearchTextField
import com.intellij.ui.components.JBList
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.treeStructure.Tree
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelperObject
import com.proboscis.pinjectdesign.kotlin.data.PyConfiguration
import com.proboscis.pinjectdesign.kotlin.error.DiagnosticRunner
import java.awt.BorderLayout
import java.awt.Component
import java.awt.event.MouseAdapter
import java.awt.event.MouseEvent
import javax.swing.*
import javax.swing.tree.DefaultMutableTreeNode
import javax.swing.tree.DefaultTreeCellRenderer
import javax.swing.tree.DefaultTreeModel
import javax.swing.tree.TreePath

/**
 * Main panel for the Pinjected tool window.
 * Displays all configurations found in the current Python file.
 */
class PinjectedToolWindowPanel(private val project: Project) : JPanel(BorderLayout()) {
    private val log = Logger.getInstance("com.proboscis.pinjectdesign.kotlin.toolwindow.PinjectedToolWindowPanel")
    
    private val treeModel = DefaultTreeModel(DefaultMutableTreeNode("No Python file selected"))
    private val tree = Tree(treeModel)
    private var currentFile: VirtualFile? = null
    private var helper: InjectedFunctionActionHelper? = null
    private var allConfigs: Map<String, List<PyConfiguration>> = emptyMap()
    private val searchField = SearchTextField()
    
    init {
        setupUI()
        setupListeners()
        updateForCurrentFile()
    }
    
    private fun setupUI() {
        // Create top panel with toolbar and search
        val topPanel = JPanel(BorderLayout())
        
        // Create toolbar
        val toolbar = createToolbar()
        topPanel.add(toolbar, BorderLayout.NORTH)
        
        // Add search field
        searchField.textEditor.emptyText.text = "Search configurations..."
        searchField.addDocumentListener(object : javax.swing.event.DocumentListener {
            override fun insertUpdate(e: javax.swing.event.DocumentEvent) = filterTree()
            override fun removeUpdate(e: javax.swing.event.DocumentEvent) = filterTree()
            override fun changedUpdate(e: javax.swing.event.DocumentEvent) = filterTree()
        })
        topPanel.add(searchField, BorderLayout.SOUTH)
        
        add(topPanel, BorderLayout.NORTH)
        
        // Setup tree
        tree.isRootVisible = true
        tree.cellRenderer = ConfigurationTreeCellRenderer()
        
        // Add mouse listeners for double-click and right-click
        tree.addMouseListener(object : MouseAdapter() {
            override fun mouseClicked(e: MouseEvent) {
                if (e.clickCount == 2) {
                    val path = tree.getPathForLocation(e.x, e.y) ?: return
                    val node = path.lastPathComponent as? DefaultMutableTreeNode ?: return
                    val config = node.userObject as? PyConfiguration ?: return
                    runConfiguration(config)
                }
            }
            
            override fun mousePressed(e: MouseEvent) {
                maybeShowPopup(e)
            }
            
            override fun mouseReleased(e: MouseEvent) {
                maybeShowPopup(e)
            }
            
            private fun maybeShowPopup(e: MouseEvent) {
                if (e.isPopupTrigger) {
                    val path = tree.getPathForLocation(e.x, e.y) ?: return
                    tree.selectionPath = path
                    val node = path.lastPathComponent as? DefaultMutableTreeNode ?: return
                    val config = node.userObject as? PyConfiguration ?: return
                    
                    showContextMenu(e, config)
                }
            }
        })
        
        // Add to scroll pane
        val scrollPane = JBScrollPane(tree)
        add(scrollPane, BorderLayout.CENTER)
        
        // Add status label at bottom
        val statusLabel = JLabel("Double-click to run configuration")
        statusLabel.border = BorderFactory.createEmptyBorder(2, 5, 2, 5)
        add(statusLabel, BorderLayout.SOUTH)
    }
    
    private fun createToolbar(): JComponent {
        val actionGroup = DefaultActionGroup()
        
        // Refresh action
        actionGroup.add(object : AnAction("Refresh", "Reload configurations", AllIcons.Actions.Refresh) {
            override fun actionPerformed(e: AnActionEvent) {
                refreshConfigurations()
            }
        })
        
        // Update cache action
        actionGroup.add(object : AnAction("Update Cache", "Clear cache and reload", AllIcons.Actions.ForceRefresh) {
            override fun actionPerformed(e: AnActionEvent) {
                updateCache()
            }
        })
        
        // Expand all action
        actionGroup.add(object : AnAction("Expand All", "Expand all nodes", AllIcons.Actions.Expandall) {
            override fun actionPerformed(e: AnActionEvent) {
                expandAll()
            }
        })
        
        // Collapse all action
        actionGroup.add(object : AnAction("Collapse All", "Collapse all nodes", AllIcons.Actions.Collapseall) {
            override fun actionPerformed(e: AnActionEvent) {
                collapseAll()
            }
        })
        
        // Separator
        actionGroup.addSeparator()
        
        // Run diagnostics action
        actionGroup.add(object : AnAction("Run Diagnostics", "Check plugin configuration", AllIcons.General.Settings) {
            override fun actionPerformed(e: AnActionEvent) {
                DiagnosticRunner.runDiagnostics(project)
            }
        })
        
        val toolbar = ActionManager.getInstance().createActionToolbar(
            "PinjectedToolWindow",
            actionGroup,
            true
        )
        toolbar.targetComponent = this
        return toolbar.component
    }
    
    private fun setupListeners() {
        // Listen for file editor changes
        project.messageBus.connect().subscribe(
            FileEditorManagerListener.FILE_EDITOR_MANAGER,
            object : FileEditorManagerListener {
                override fun fileOpened(source: FileEditorManager, file: VirtualFile) {
                    if (file.extension == "py") {
                        updateForFile(file)
                    }
                }
                
                override fun selectionChanged(event: FileEditorManagerEvent) {
                    event.newFile?.let { file ->
                        if (file.extension == "py") {
                            updateForFile(file)
                        }
                    }
                }
            }
        )
    }
    
    private fun updateForCurrentFile() {
        val editor = FileEditorManager.getInstance(project).selectedEditor
        val file = editor?.file
        if (file?.extension == "py") {
            updateForFile(file)
        }
    }
    
    private fun updateForFile(file: VirtualFile) {
        currentFile = file
        helper = InjectedFunctionActionHelperObject.createSafely(project)
        
        if (helper == null) {
            updateTreeForNoPython()
            return
        }
        
        refreshConfigurations()
    }
    
    private fun refreshConfigurations() {
        val file = currentFile ?: return
        val h = helper ?: return
        
        log.info("Refreshing configurations for: ${file.path}")
        
        // Update tree to show loading
        SwingUtilities.invokeLater {
            val root = DefaultMutableTreeNode("Loading configurations...")
            treeModel.setRoot(root)
        }
        
        // Load configurations in background
        h.runInBackground("Loading configurations") { indicator ->
            try {
                val configs = InjectedFunctionActionHelperObject.cache[file.path] 
                    ?: h.findConfigurations(file.path)
                
                SwingUtilities.invokeLater {
                    updateTreeWithConfigurations(file.name, configs)
                }
            } catch (e: Exception) {
                log.error("Failed to load configurations", e)
                SwingUtilities.invokeLater {
                    updateTreeForError(e.message ?: "Unknown error")
                }
            }
        }
    }
    
    private fun updateCache() {
        val file = currentFile ?: return
        val h = helper ?: return
        
        h.runInBackground("Updating configuration cache") { indicator ->
            try {
                // Clear cache
                InjectedFunctionActionHelperObject.cache.remove(file.path)
                
                // Reload
                val configs = h.findConfigurations(file.path)
                InjectedFunctionActionHelperObject.cache[file.path] = configs
                
                SwingUtilities.invokeLater {
                    updateTreeWithConfigurations(file.name, configs)
                }
            } catch (e: Exception) {
                log.error("Failed to update cache", e)
                SwingUtilities.invokeLater {
                    updateTreeForError(e.message ?: "Unknown error")
                }
            }
        }
    }
    
    private fun updateTreeWithConfigurations(fileName: String, configs: Map<String, List<PyConfiguration>>) {
        allConfigs = configs
        searchField.text = "" // Clear search when updating
        rebuildTree(fileName, configs)
    }
    
    private fun rebuildTree(fileName: String, configs: Map<String, List<PyConfiguration>>) {
        val root = DefaultMutableTreeNode(fileName)
        
        if (configs.isEmpty()) {
            root.add(DefaultMutableTreeNode("No configurations found"))
        } else {
            // Group by configuration name
            configs.forEach { (groupName, configList) ->
                val groupNode = DefaultMutableTreeNode(groupName)
                
                configList.forEach { config ->
                    val configNode = DefaultMutableTreeNode(config)
                    groupNode.add(configNode)
                }
                
                root.add(groupNode)
            }
        }
        
        treeModel.setRoot(root)
        
        // Expand root and first level
        tree.expandPath(TreePath(root))
        for (i in 0 until root.childCount) {
            val child = root.getChildAt(i) as DefaultMutableTreeNode
            tree.expandPath(TreePath(arrayOf(root, child)))
        }
    }
    
    private fun filterTree() {
        val searchText = searchField.text.lowercase()
        if (searchText.isEmpty()) {
            rebuildTree(currentFile?.name ?: "No file", allConfigs)
            return
        }
        
        // Filter configurations
        val filteredConfigs = mutableMapOf<String, List<PyConfiguration>>()
        allConfigs.forEach { (groupName, configList) ->
            val filteredList = configList.filter { config ->
                config.name.lowercase().contains(searchText) ||
                groupName.lowercase().contains(searchText) ||
                config.arguments.any { it.lowercase().contains(searchText) }
            }
            if (filteredList.isNotEmpty()) {
                filteredConfigs[groupName] = filteredList
            }
        }
        
        rebuildTree(currentFile?.name ?: "No file", filteredConfigs)
    }
    
    private fun updateTreeForNoPython() {
        val root = DefaultMutableTreeNode("Python not configured")
        root.add(DefaultMutableTreeNode("Please configure Python interpreter"))
        root.add(DefaultMutableTreeNode("Then click 'Refresh' button"))
        treeModel.setRoot(root)
    }
    
    private fun updateTreeForError(error: String) {
        val root = DefaultMutableTreeNode("Error loading configurations")
        root.add(DefaultMutableTreeNode(error))
        root.add(DefaultMutableTreeNode("Click 'Run Diagnostics' for more info"))
        treeModel.setRoot(root)
    }
    
    private fun runConfiguration(config: PyConfiguration) {
        val h = helper ?: return
        
        log.info("Running configuration: ${config.name}")
        h.runInBackground("Running ${config.name}") { indicator ->
            h.runConfig(config)
        }
    }
    
    private fun expandAll() {
        for (i in 0 until tree.rowCount) {
            tree.expandRow(i)
        }
    }
    
    private fun collapseAll() {
        for (i in tree.rowCount - 1 downTo 1) {
            tree.collapseRow(i)
        }
    }
    
    private fun showContextMenu(e: MouseEvent, config: PyConfiguration) {
        val menu = JPopupMenu()
        
        // Run action
        val runAction = JMenuItem("Run", AllIcons.Actions.Execute)
        runAction.addActionListener {
            runConfiguration(config)
        }
        menu.add(runAction)
        
        menu.addSeparator()
        
        // Copy actions
        val copyNameAction = JMenuItem("Copy Name", AllIcons.Actions.Copy)
        copyNameAction.addActionListener {
            val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
            val selection = java.awt.datatransfer.StringSelection(config.name)
            clipboard.setContents(selection, selection)
        }
        menu.add(copyNameAction)
        
        val copyCommandAction = JMenuItem("Copy Command", AllIcons.Actions.Copy)
        copyCommandAction.addActionListener {
            val command = "${config.interpreter_path} ${config.script_path} ${config.arguments.joinToString(" ")}"
            val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
            val selection = java.awt.datatransfer.StringSelection(command)
            clipboard.setContents(selection, selection)
        }
        menu.add(copyCommandAction)
        
        val copyArgsAction = JMenuItem("Copy Arguments", AllIcons.Actions.Copy)
        copyArgsAction.addActionListener {
            val args = config.arguments.joinToString(" ")
            val clipboard = java.awt.Toolkit.getDefaultToolkit().systemClipboard
            val selection = java.awt.datatransfer.StringSelection(args)
            clipboard.setContents(selection, selection)
        }
        menu.add(copyArgsAction)
        
        menu.show(e.component, e.x, e.y)
    }
    
    /**
     * Custom cell renderer for the configuration tree.
     */
    private class ConfigurationTreeCellRenderer : DefaultTreeCellRenderer() {
        override fun getTreeCellRendererComponent(
            tree: JTree,
            value: Any?,
            sel: Boolean,
            expanded: Boolean,
            leaf: Boolean,
            row: Int,
            hasFocus: Boolean
        ): Component {
            super.getTreeCellRendererComponent(tree, value, sel, expanded, leaf, row, hasFocus)
            
            val node = value as? DefaultMutableTreeNode
            when (val userObject = node?.userObject) {
                is PyConfiguration -> {
                    text = userObject.name
                    icon = AllIcons.Actions.Execute
                    toolTipText = buildString {
                        append("<html>")
                        append("<b>${userObject.name}</b><br>")
                        append("Script: ${userObject.script_path}<br>")
                        append("Args: ${userObject.arguments.joinToString(" ")}<br>")
                        append("Working dir: ${userObject.working_dir}")
                        append("</html>")
                    }
                }
                is String -> {
                    text = userObject
                    icon = when {
                        userObject.contains("error", ignoreCase = true) -> AllIcons.General.Error
                        userObject.contains("No configurations") -> AllIcons.General.Warning
                        userObject.contains("Loading") -> AllIcons.Process.Step_1
                        leaf -> AllIcons.General.Information
                        else -> AllIcons.Nodes.Folder
                    }
                }
            }
            
            return this
        }
    }
}