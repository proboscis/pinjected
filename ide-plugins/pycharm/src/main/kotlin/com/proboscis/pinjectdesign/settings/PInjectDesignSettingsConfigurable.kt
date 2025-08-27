package com.proboscis.pinjectdesign.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.ui.DialogPanel
import com.intellij.ui.dsl.builder.panel
import com.intellij.ui.dsl.builder.bindSelected
import javax.swing.JComponent

class PInjectDesignSettingsConfigurable : Configurable {
    private var settingsComponent: DialogPanel? = null

    override fun getDisplayName(): String = "PInject Design"

    override fun createComponent(): JComponent {
        val settings = PInjectDesignSettings.getInstance()
        settingsComponent = panel {
            row("Enable gutter icons:") {
                checkBox("Show gutter icons for injected functions")
                    .bindSelected(settings::enableGutterIcons)
            }
            row("Enable visualization:") {
                checkBox("Enable dependency graph visualization")
                    .bindSelected(settings::enableVisualization)
            }
        }
        return settingsComponent!!
    }

    override fun isModified(): Boolean {
        return settingsComponent?.isModified() ?: false
    }

    override fun apply() {
        settingsComponent?.apply()
    }

    override fun reset() {
        settingsComponent?.reset()
    }

    override fun disposeUIResources() {
        settingsComponent = null
    }
}
