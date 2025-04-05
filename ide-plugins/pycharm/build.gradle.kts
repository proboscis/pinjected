plugins {
    id("org.jetbrains.intellij") version "1.17.2"
    id("java")
    kotlin("jvm") version "1.9.22"
    kotlin("plugin.serialization") version "1.9.22"
}

group = "com.proboscis.pinjectdesign"
version = "0.1.0"

repositories {
    mavenCentral()
}

dependencies {
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
    
    // Add test dependencies
    testImplementation("org.jetbrains.kotlin:kotlin-test")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit")
    testImplementation("org.mockito:mockito-core:3.12.4")
    testImplementation("org.mockito.kotlin:mockito-kotlin:3.2.0")
}

// Configure Gradle IntelliJ Plugin
intellij {
    version.set("2024.3") // Same version as your PyCharm
    type.set("PY") // PyCharm Professional
    plugins.set(listOf("python")) // This is the built-in Python plugin
}

tasks {
    patchPluginXml {
        sinceBuild.set("243")
        untilBuild.set("")
        changeNotes.set("""
            <ul>
                <li>Initial release</li>
            </ul>
        """)
    }
    
    // Set the JVM compatibility versions
    withType<JavaCompile> {
        sourceCompatibility = "17"
        targetCompatibility = "17"
    }
    
    withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
        kotlinOptions.jvmTarget = "17"
    }
}
