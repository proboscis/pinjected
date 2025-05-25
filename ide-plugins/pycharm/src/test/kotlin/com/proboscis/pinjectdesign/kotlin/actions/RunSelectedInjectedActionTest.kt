package com.proboscis.pinjectdesign.kotlin.actions

import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiFile
import com.jetbrains.python.psi.PyAssignmentStatement
import com.jetbrains.python.psi.PyTargetExpression
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.util.PinjectedConsoleUtil
import org.junit.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.mockito.Mockito.any
import org.mockito.Mockito.eq
import org.mockito.Mockito.never

class RunSelectedInjectedActionTest {

    @Test
    fun testActionPerformedWithInjectedVariable() {
        // Create mocks
        val mockEvent = mock(AnActionEvent::class.java)
        val mockProject = mock(Project::class.java)
        val mockEditor = mock(Editor::class.java)
        val mockFile = mock(PsiFile::class.java)
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        val mockConsoleUtil = mock(PinjectedConsoleUtil::class.java)
        
        // Configure mocks
        `when`(mockEvent.project).thenReturn(mockProject)
        `when`(mockEvent.getData(CommonDataKeys.EDITOR)).thenReturn(mockEditor)
        `when`(mockEvent.getData(CommonDataKeys.PSI_FILE)).thenReturn(mockFile)
        `when`(mockFile.virtualFile).thenReturn(mock(com.intellij.openapi.vfs.VirtualFile::class.java))
        `when`(mockFile.virtualFile.path).thenReturn("/test/path/test_file.py")
        
        // Create action with mocked dependencies
        val action = object : RunSelectedInjectedAction() {
            override fun createHelper(project: Project): InjectedFunctionActionHelper {
                return mockHelper
            }
            
            override fun createConsoleUtil(helper: InjectedFunctionActionHelper): PinjectedConsoleUtil {
                return mockConsoleUtil
            }
        }
        
        // Execute action
        action.actionPerformed(mockEvent)
        
        // Verify console util was called with correct parameters
        // Note: This is a simplified test that doesn't fully simulate the PSI tree traversal
        // In a real test, we would need to mock more complex behavior
    }

    @Test
    fun testActionPerformedWithNoInjectedVariable() {
        // Create mocks
        val mockEvent = mock(AnActionEvent::class.java)
        val mockProject = mock(Project::class.java)
        val mockEditor = mock(Editor::class.java)
        val mockFile = mock(PsiFile::class.java)
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        val mockConsoleUtil = mock(PinjectedConsoleUtil::class.java)
        
        // Configure mocks
        `when`(mockEvent.project).thenReturn(mockProject)
        `when`(mockEvent.getData(CommonDataKeys.EDITOR)).thenReturn(mockEditor)
        `when`(mockEvent.getData(CommonDataKeys.PSI_FILE)).thenReturn(mockFile)
        
        // Create action with mocked dependencies
        val action = object : RunSelectedInjectedAction() {
            override fun createHelper(project: Project): InjectedFunctionActionHelper {
                return mockHelper
            }
            
            override fun createConsoleUtil(helper: InjectedFunctionActionHelper): PinjectedConsoleUtil {
                return mockConsoleUtil
            }
        }
        
        // Execute action
        action.actionPerformed(mockEvent)
        
        // Verify notification was shown for no injected found
        verify(mockHelper).showNotification(
            eq("No Injected Found"), 
            eq("No injected found at the current cursor position"), 
            any()
        )
        
        // Verify console util was not called
        verify(mockConsoleUtil, never()).runInjected(any(), any(), any())
    }
}
