package com.proboscis.pinjectdesign.settings;

import com.intellij.openapi.components.PersistentStateComponent;
import com.intellij.openapi.components.Service;
import com.intellij.openapi.components.State;
import com.intellij.openapi.components.Storage;
import com.intellij.util.xmlb.XmlSerializerUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

@Service
@State(
    name = "com.proboscis.pinjectdesign.settings.PInjectDesignSettings",
    storages = @Storage("PInjectDesignSettings.xml")
)
public class PInjectDesignSettings implements PersistentStateComponent<PInjectDesignSettings> {
    public boolean enableDetailedAnalysis = false;
    public boolean checkForDependencies = true;
    public boolean enableCodeCompletion = true;
    
    @Override
    public @Nullable PInjectDesignSettings getState() {
        return this;
    }
    
    @Override
    public void loadState(@NotNull PInjectDesignSettings state) {
        XmlSerializerUtil.copyBean(state, this);
    }
}
