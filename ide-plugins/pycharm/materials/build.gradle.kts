plugins {
    id("java")
    id("org.jetbrains.kotlin.jvm") version "1.9.23"
    id("org.jetbrains.intellij") version "1.17.4"
    kotlin("plugin.serialization") version "1.9.23"
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

group = "com.proboscis"
version = "1.0.14"

repositories {
    mavenCentral()
    maven("https://www.jetbrains.com/intellij-repository/releases")
}

dependencies {
    implementation("com.theokanning.openai-gpt3-java:service:0.18.2")
    implementation("com.theokanning.openai-gpt3-java:api:0.18.2")
    implementation("com.theokanning.openai-gpt3-java:client:0.18.2")
    implementation(platform("com.squareup.okhttp3:okhttp-bom:4.12.0"))
    implementation("com.squareup.okhttp3:okhttp")
    implementation("com.squareup.okhttp3:logging-interceptor")
    implementation("org.junit.jupiter:junit-jupiter:5.10.2")
    implementation("org.json:json:20240303")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3") // 最新版に修正
    implementation("org.zeromq:jeromq:0.5.4")
    implementation("org.jetbrains.kotlin:kotlin-scripting-compiler-embeddable:1.9.23") // 最新Kotlinに修正
    implementation("org.jetbrains.kotlin:kotlin-scripting-compiler-impl-embeddable:1.9.23") // 最新Kotlinに修正
}

intellij {
    version.set("2024.3.5")
    type.set("IU")
    plugins.set(listOf("Pythonid:243.26053.27"))
}
tasks.withType<JavaCompile> {
    sourceCompatibility = "21"
    targetCompatibility = "21"
}
tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
    kotlinOptions {
        jvmTarget = "21"
        apiVersion = "1.9"
        languageVersion = "1.9"
    }
}

tasks {
    withType<JavaCompile> {
        sourceCompatibility = "21"
        targetCompatibility = "21"
    }
    withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile> {
        kotlinOptions {
            jvmTarget = "21"
            apiVersion = "1.9"
            languageVersion = "1.9"
        }
    }

    patchPluginXml {
        sinceBuild.set("243")    // IntelliJ 2024.3 は243.*
        untilBuild.set("243.*")
    }

    signPlugin {
        certificateChain.set(System.getenv("CERTIFICATE_CHAIN"))
        privateKey.set(System.getenv("PRIVATE_KEY"))
        password.set(System.getenv("PRIVATE_KEY_PASSWORD"))
    }

    publishPlugin {
        token.set(System.getenv("PUBLISH_TOKEN"))
    }
}