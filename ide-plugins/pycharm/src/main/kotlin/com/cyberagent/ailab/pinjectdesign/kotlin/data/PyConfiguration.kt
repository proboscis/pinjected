package com.cyberagent.ailab.pinjectdesign.kotlin.data

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
