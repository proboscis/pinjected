package com.proboscis.kotlinopenai

import com.proboscis.kotlinopenai.chatgpt.OpenAIUtil

class MyActionTest {

    @org.junit.jupiter.api.Test
    fun generateText() {
        val openAIUtil = OpenAIUtil("YOUR_API_KEY_HERE")
        val res = openAIUtil.generateText("Hello, how are you? what's your name?")
        println(res)
    }
}