package com.proboscis.pinjectdesign.settings;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.options.Configurable;
import com.intellij.openapi.options.ConfigurationException;
import org.jetbrains.annotations.Nls;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;

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
        
        enableDetailedAnalysisCheckBox = new JCheckBox("Enable detailed analysis");
        checkForDependenciesCheckBox = new JCheckBox("Check for dependencies");
        
        mainPanel.add(enableDetailedAnalysisCheckBox);
        mainPanel.add(checkForDependenciesCheckBox);
        
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
