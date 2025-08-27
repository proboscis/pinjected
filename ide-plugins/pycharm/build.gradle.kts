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
    implementation("com.google.code.gson:gson:2.10.1")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.mockito:mockito-core:5.2.0")
    testImplementation("org.mockito.kotlin:mockito-kotlin:5.2.0")
    
    // Note: Remote Robot dependencies commented out - need special repository setup
    // testImplementation("com.intellij.remoterobot:remote-robot:0.11.16")
    // testImplementation("com.intellij.remoterobot:remote-fixtures:0.11.16")
}

// Configure Gradle IntelliJ Plugin
intellij {
    version.set("2024.3") // Same version as your PyCharm
    type.set("PY") // PyCharm Professional
    plugins.set(listOf("python")) // This is the built-in Python plugin
    downloadSources.set(true)
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
    
    test {
        useJUnit()
        testLogging {
            events("passed", "skipped", "failed")
            showStandardStreams = true
        }
    }
}
