package com.cyberagent.ailab.pinjectdesign.actions;

import com.cyberagent.ailab.pinjectdesign.settings.PInjectDesignSettings;
import com.cyberagent.ailab.pinjectdesign.util.PythonUtils;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.components.Service;
import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.module.ModuleUtilCore;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.psi.PsiFile;
import com.jetbrains.python.psi.PyClass;
import com.jetbrains.python.psi.PyFile;
import org.jetbrains.annotations.NotNull;

import java.util.Map;

public class AnalyzePythonCodeAction extends AnAction {
    @Override
    public void update(@NotNull AnActionEvent e) {
        // Enable the action only for Python files
        Project project = e.getProject();
        Editor editor = e.getData(CommonDataKeys.EDITOR);
        PsiFile psiFile = e.getData(CommonDataKeys.PSI_FILE);

        boolean isPythonFile = psiFile instanceof PyFile;
        e.getPresentation().setEnabledAndVisible(project != null && editor != null && isPythonFile);
    }

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        Project project = e.getProject();
        PsiFile psiFile = e.getData(CommonDataKeys.PSI_FILE);
        
        if (project == null || !(psiFile instanceof PyFile)) {
            return;
        }
        
        PyFile pyFile = (PyFile) psiFile;
        String fileName = pyFile.getName();
        int functionCount = pyFile.getTopLevelFunctions().size();
        int classCount = pyFile.getTopLevelClasses().size();
        
        // Get plugin settings
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        
        StringBuilder messageBuilder = new StringBuilder();
        messageBuilder.append(String.format(
            "Python File Analysis:\n" +
            "File: %s\n" +
            "Functions: %d\n" +
            "Classes: %d\n",
            fileName, functionCount, classCount
        ));
        
        // If detailed analysis is enabled, provide more info
        if (settings.enableDetailedAnalysis) {
            Map<String, Object> analysisResults = PythonUtils.analyzePythonFileForDI(pyFile);
            
            @SuppressWarnings("unchecked")
            var dependencyConstructors = (java.util.List<Map<String, String>>) analysisResults.get("dependencyConstructors");
            
            if (!dependencyConstructors.isEmpty()) {
                messageBuilder.append("\nDependency Injection Analysis:\n");
                
                for (Map<String, String> constructor : dependencyConstructors) {
                    messageBuilder.append(String.format(
                        "Class: %s\nDependencies: %s\n\n",
                        constructor.get("className"),
                        constructor.get("dependencies")
                    ));
                }
            } else {
                messageBuilder.append("\nNo dependency injection patterns detected.");
            }
        }
        
        // Check for recommended dependencies if enabled
        if (settings.checkForDependencies) {
            Module module = ModuleUtilCore.findModuleForPsiElement(psiFile);
            if (module != null) {
                messageBuilder.append("\nDependency Status:\n");
                
                String[] diLibraries = {"injector", "dependency-injector", "pinject"};
                boolean hasDiLibrary = false;
                
                for (String lib : diLibraries) {
                    boolean isInstalled = PythonUtils.isPackageInstalled(module, lib);
                    messageBuilder.append(String.format("- %s: %s\n", lib, isInstalled ? "Installed" : "Not installed"));
                    hasDiLibrary |= isInstalled;
                }
                
                if (!hasDiLibrary && classCount > 0) {
                    messageBuilder.append("\nRecommendation: Consider installing a dependency injection library.");
                }
            }
        }
        
        Messages.showInfoMessage(project, messageBuilder.toString(), "Python Code Analysis");
    }
}