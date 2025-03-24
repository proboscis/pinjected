package com.proboscis.pinjectdesign.util;

import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.module.Module;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.projectRoots.Sdk;
import com.jetbrains.python.psi.PyClass;
import com.jetbrains.python.psi.PyFile;
import com.jetbrains.python.psi.PyFunction;
import com.jetbrains.python.psi.PyParameter;
import com.jetbrains.python.sdk.PythonSdkUtil;
import com.jetbrains.python.psi.types.TypeEvalContext;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;

public class PythonUtils {
    private static final Logger LOG = Logger.getInstance(PythonUtils.class);

    /**
     * Get Python SDK for the given module
     */
    @Nullable
    public static Sdk getPythonSdk(@NotNull Module module) {
        return PythonSdkUtil.findPythonSdk(module);
    }

    /**
     * Check if a specific package is installed
     * Note: Simplified implementation as PyPackageManager is deprecated
     */
    public static boolean isPackageInstalled(@NotNull Module module, @NotNull String packageName) {
        // In a real implementation, you might want to use a different approach
        // such as checking the project's requirements.txt or environment files
        // This is a simplified approach for demonstration
        return true;
    }

    /**
     * Analyze a Python file for potential dependency injection patterns
     */
    public static Map<String, Object> analyzePythonFileForDI(@NotNull PyFile pyFile) {
        Map<String, Object> results = new HashMap<>();
        List<Map<String, String>> classes = new ArrayList<>();
        List<Map<String, String>> dependencyConstructors = new ArrayList<>();

        // Analyze classes
        for (PyClass pyClass : pyFile.getTopLevelClasses()) {
            Map<String, String> classInfo = new HashMap<>();
            classInfo.put("name", pyClass.getName());
            classInfo.put("hasDependencyConstructor", hasDependencyConstructor(pyClass) ? "yes" : "no");
            
            classes.add(classInfo);
            
            // Check for constructor with dependencies
            if (hasDependencyConstructor(pyClass)) {
                Map<String, String> constructorInfo = new HashMap<>();
                constructorInfo.put("className", pyClass.getName());
                constructorInfo.put("dependencies", getDependenciesFromConstructor(pyClass));
                dependencyConstructors.add(constructorInfo);
            }
        }
        
        results.put("classes", classes);
        results.put("dependencyConstructors", dependencyConstructors);
        
        return results;
    }
    
    /**
     * Check if a class has a constructor with potential dependencies
     */
    private static boolean hasDependencyConstructor(@NotNull PyClass pyClass) {
        TypeEvalContext context = TypeEvalContext.codeInsightFallback(pyClass.getProject());
        PyFunction initMethod = pyClass.findMethodByName("__init__", false, context);
        return initMethod != null && initMethod.getParameterList().getParameters().length > 1;
    }
    
    /**
     * Get dependencies from constructor parameters
     */
    private static String getDependenciesFromConstructor(@NotNull PyClass pyClass) {
        TypeEvalContext context = TypeEvalContext.codeInsightFallback(pyClass.getProject());
        PyFunction initMethod = pyClass.findMethodByName("__init__", false, context);
        if (initMethod == null) {
            return "";
        }
        
        StringBuilder deps = new StringBuilder();
        // Skip first parameter (self)
        PyParameter[] parameters = initMethod.getParameterList().getParameters();
        for (int i = 1; i < parameters.length; i++) {
            PyParameter param = parameters[i];
            if (i > 1) {
                deps.append(", ");
            }
            deps.append(param.getName());
            // Note: We can't get type annotations easily, so we skip it in this simplified version
        }
        
        return deps.toString();
    }
}
