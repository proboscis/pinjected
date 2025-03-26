package com.proboscis.pinjectdesign.settings;

import com.intellij.openapi.application.ApplicationManager;
import com.intellij.openapi.options.Configurable;
import com.intellij.openapi.options.ConfigurationException;
import org.jetbrains.annotations.Nls;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import javax.swing.border.BorderFactory;
import java.awt.Font;

public class PInjectDesignSettingsConfigurable implements Configurable {
    private JPanel mainPanel;
    private JCheckBox enableDetailedAnalysisCheckBox;
    private JCheckBox checkForDependenciesCheckBox;
    private JCheckBox enableCodeCompletionCheckBox;
    
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
        settingsPanel.setBorder(BorderFactory.createTitledBorder("Settings"));
        
        enableDetailedAnalysisCheckBox = new JCheckBox("Enable detailed analysis");
        JLabel detailedAnalysisDescription = new JLabel("    Enables more comprehensive analysis of Python code structure");
        detailedAnalysisDescription.setFont(detailedAnalysisDescription.getFont().deriveFont(Font.ITALIC));
        
        checkForDependenciesCheckBox = new JCheckBox("Check for dependencies");
        JLabel dependenciesDescription = new JLabel("    Verifies dependencies when analyzing injected functions");
        dependenciesDescription.setFont(dependenciesDescription.getFont().deriveFont(Font.ITALIC));
        
        enableCodeCompletionCheckBox = new JCheckBox("Enable code completion");
        JLabel codeCompletionDescription = new JLabel("    Shows code completion suggestions for injected functions");
        codeCompletionDescription.setFont(codeCompletionDescription.getFont().deriveFont(Font.ITALIC));
        
        settingsPanel.add(enableDetailedAnalysisCheckBox);
        settingsPanel.add(detailedAnalysisDescription);
        settingsPanel.add(Box.createVerticalStrut(5));
        
        settingsPanel.add(checkForDependenciesCheckBox);
        settingsPanel.add(dependenciesDescription);
        settingsPanel.add(Box.createVerticalStrut(5));
        
        settingsPanel.add(enableCodeCompletionCheckBox);
        settingsPanel.add(codeCompletionDescription);
        
        mainPanel.add(settingsPanel);
        
        // Initialize values from settings
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        enableDetailedAnalysisCheckBox.setSelected(settings.enableDetailedAnalysis);
        checkForDependenciesCheckBox.setSelected(settings.checkForDependencies);
        enableCodeCompletionCheckBox.setSelected(settings.enableCodeCompletion);
        
        return mainPanel;
    }
    
    @Override
    public boolean isModified() {
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        return enableDetailedAnalysisCheckBox.isSelected() != settings.enableDetailedAnalysis ||
               checkForDependenciesCheckBox.isSelected() != settings.checkForDependencies ||
               enableCodeCompletionCheckBox.isSelected() != settings.enableCodeCompletion;
    }
    
    @Override
    public void apply() throws ConfigurationException {
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        settings.enableDetailedAnalysis = enableDetailedAnalysisCheckBox.isSelected();
        settings.checkForDependencies = checkForDependenciesCheckBox.isSelected();
        settings.enableCodeCompletion = enableCodeCompletionCheckBox.isSelected();
    }
    
    @Override
    public void reset() {
        PInjectDesignSettings settings = ApplicationManager.getApplication().getService(PInjectDesignSettings.class);
        enableDetailedAnalysisCheckBox.setSelected(settings.enableDetailedAnalysis);
        checkForDependenciesCheckBox.setSelected(settings.checkForDependencies);
        enableCodeCompletionCheckBox.setSelected(settings.enableCodeCompletion);
    }
    
    @Override
    public void disposeUIResources() {
        mainPanel = null;
        enableDetailedAnalysisCheckBox = null;
        checkForDependenciesCheckBox = null;
        enableCodeCompletionCheckBox = null;
    }
}
