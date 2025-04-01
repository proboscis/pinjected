package com.proboscis.pinjectdesign.settings;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.options.Configurable;
import com.intellij.openapi.options.ConfigurationException;
import org.jetbrains.annotations.Nls;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import java.awt.Font;

public class PInjectDesignSettingsConfigurable implements Configurable {
    private JPanel mainPanel;
    private JCheckBox enableDetailedAnalysisCheckBox;
    private JCheckBox checkForDependenciesCheckBox;
    
    @Nls(capitalization = Nls.Capitalization.Title)
    @Override
    public String getDisplayName() {
        return "PInject Design";
    }
    
    @Override
    public @Nullable JComponent createComponent() {
        mainPanel = new JPanel();
        mainPanel.setLayout(new BoxLayout(mainPanel, BoxLayout.Y_AXIS));
        
        JPanel settingsPanel = new JPanel();
        settingsPanel.setLayout(new BoxLayout(settingsPanel, BoxLayout.Y_AXIS));
        settingsPanel.setBorder(javax.swing.BorderFactory.createTitledBorder("Settings"));
        
        enableDetailedAnalysisCheckBox = new JCheckBox("Enable detailed analysis");
        JLabel detailedAnalysisDescription = new JLabel("    Analyzes classes with multiple constructor parameters using PythonUtils.analyzePythonFileForDI()");
        detailedAnalysisDescription.setFont(detailedAnalysisDescription.getFont().deriveFont(Font.ITALIC));
        
        checkForDependenciesCheckBox = new JCheckBox("Check for dependencies");
        JLabel dependenciesDescription = new JLabel("    Checks if DI libraries (injector, dependency-injector, pinject) are installed via PythonUtils.isPackageInstalled()");
        dependenciesDescription.setFont(dependenciesDescription.getFont().deriveFont(Font.ITALIC));
        

        
        settingsPanel.add(enableDetailedAnalysisCheckBox);
        settingsPanel.add(detailedAnalysisDescription);
        settingsPanel.add(Box.createVerticalStrut(5));
        
        settingsPanel.add(checkForDependenciesCheckBox);
        settingsPanel.add(dependenciesDescription);
        settingsPanel.add(Box.createVerticalStrut(5));
        

        
        mainPanel.add(settingsPanel);
        
        // Initialize values from settings
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        enableDetailedAnalysisCheckBox.setSelected(settings.enableDetailedAnalysis);
        checkForDependenciesCheckBox.setSelected(settings.checkForDependencies);
        
        return mainPanel;
    }
    
    @Override
    public boolean isModified() {
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        return enableDetailedAnalysisCheckBox.isSelected() != settings.enableDetailedAnalysis ||
               checkForDependenciesCheckBox.isSelected() != settings.checkForDependencies;
    }
    
    @Override
    public void apply() throws ConfigurationException {
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        settings.enableDetailedAnalysis = enableDetailedAnalysisCheckBox.isSelected();
        settings.checkForDependencies = checkForDependenciesCheckBox.isSelected();
    }
    
    @Override
    public void reset() {
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        enableDetailedAnalysisCheckBox.setSelected(settings.enableDetailedAnalysis);
        checkForDependenciesCheckBox.setSelected(settings.checkForDependencies);
    }
    
    @Override
    public void disposeUIResources() {
        mainPanel = null;
        enableDetailedAnalysisCheckBox = null;
        checkForDependenciesCheckBox = null;
    }
}
