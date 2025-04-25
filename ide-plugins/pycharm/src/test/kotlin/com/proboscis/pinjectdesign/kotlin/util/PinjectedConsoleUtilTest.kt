package com.proboscis.pinjectdesign.kotlin.util

import com.intellij.openapi.project.Project
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.data.CodeBlock
import org.junit.Assert.assertEquals
import org.junit.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`

class PinjectedConsoleUtilTest {

    @Test
    fun testRunInjected() {
        // Create mocks
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        val mockProject = mock(Project::class.java)
        val mockCodeBlock = CodeBlock("print('test')")
        
        // Configure mocks
        `when`(mockHelper.project).thenReturn(mockProject)
        `when`(mockHelper.runPythonJson<CodeBlock>(listOf("-m", "pinjected.ide_supports.console_run_helper", 
                "generate-code-with-reload", "test_script.py", "test_func")))
            .thenReturn(mockCodeBlock)
        
        // Create console util
        val consoleUtil = PinjectedConsoleUtil(mockHelper)
        
        // Call method
        consoleUtil.runInjected("test_script.py", "test_func")
        
        // Verify helper was called with correct parameters
        verify(mockHelper).runPythonJson<CodeBlock>(
            listOf("-m", "pinjected.ide_supports.console_run_helper", 
                  "generate-code-with-reload", "test_script.py", "test_func")
        )
    }

    @Test
    fun testRunPinjectedCommand() {
        // Create mocks
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        val mockProject = mock(Project::class.java)
        val mockCodeBlock = CodeBlock("print('test')")
        
        // Configure mocks
        `when`(mockHelper.project).thenReturn(mockProject)
        `when`(mockHelper.runPythonJson<CodeBlock>(listOf("-m", "pinjected.ide_supports.console_run_helper", 
                "test-command", "test_script.py", "test_func")))
            .thenReturn(mockCodeBlock)
        
        // Create console util
        val consoleUtil = PinjectedConsoleUtil(mockHelper)
        
        // Call method
        consoleUtil.runPinjectedCommand("test_script.py", "test_func", "test-command")
        
        // Verify helper was called with correct parameters
        verify(mockHelper).runPythonJson<CodeBlock>(
            listOf("-m", "pinjected.ide_supports.console_run_helper", 
                  "test-command", "test_script.py", "test_func")
        )
    }
}
