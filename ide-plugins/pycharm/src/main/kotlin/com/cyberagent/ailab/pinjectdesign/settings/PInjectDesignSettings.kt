package com.cyberagent.ailab.pinjectdesign.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.util.xmlb.XmlSerializerUtil

@State(
    name = "com.cyberagent.ailab.pinjectdesign.settings.PInjectDesignSettings",
    storages = [Storage("PInjectDesignSettings.xml")]
)
class PInjectDesignSettings : PersistentStateComponent<PInjectDesignSettings> {
    var enableGutterIcons: Boolean = true
    var enableVisualization: Boolean = true

    override fun getState(): PInjectDesignSettings = this

    override fun loadState(state: PInjectDesignSettings) {
        XmlSerializerUtil.copyBean(state, this)
    }

    companion object {
        fun getInstance(): PInjectDesignSettings {
            return ApplicationManager.getApplication().getService(PInjectDesignSettings::class.java)
        }
    }
}
