package com.proboscis.pinjectdesign.kotlin.data

/**
 * Represents an action that can be executed when clicking on a gutter icon.
 */
data class ActionItem(val name: String, val action: () -> Unit)
