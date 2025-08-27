package com.proboscis.pinjectdesign.kotlin.data

import kotlinx.serialization.KSerializer
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

@Serializable
data class PyConfiguration(
    val name: String,
    val script_path: String,
    val interpreter_path: String,
    val arguments: List<String>,
    val working_dir: String
)

@Serializable
data class ConfigurationWrapper(val configs: Map<String, List<PyConfiguration>>)

@Serializable
data class CodeBlock(
    val code: String
)

@Serializable
data class CustomCompletion(
    val name: String,
    val description: String,
    val tail: String,
)

@Serializable
data class BindingLocation(
    val type: String,
    val value: String
)

@Serializable
data class DesignMetadata(
    val key: String,
    val location: BindingLocation
)

// ActionItem moved to its own file

/**
 * Extension function to extract JSON content from a string that might be wrapped in <pinjected> tags.
 * @return The extracted JSON content.
 */
fun String.extractPinjectedContent(): String {
    val trimmed = this.trim()
    return if (trimmed.contains("<pinjected>")) {
        val pattern = Regex("<pinjected>(.*?)</pinjected>", RegexOption.DOT_MATCHES_ALL)
        val match = pattern.find(trimmed)
        match?.groupValues?.get(1)?.trim() ?: throw IllegalStateException("Failed to parse JSON from <pinjected> tags")
    } else {
        trimmed
    }
}
