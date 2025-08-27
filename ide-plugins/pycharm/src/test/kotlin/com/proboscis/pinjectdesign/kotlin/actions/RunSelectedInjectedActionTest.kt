package com.proboscis.pinjectdesign.kotlin.actions

import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.CaretModel
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.proboscis.pinjectdesign.kotlin.InjectedFunctionActionHelper
import com.proboscis.pinjectdesign.kotlin.util.PinjectedDetectionUtil
import com.proboscis.pinjectdesign.kotlin.util.GutterActionUtil
import com.intellij.notification.NotificationType
import org.junit.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.verify
import org.mockito.Mockito.`when`
import org.mockito.Mockito.any
import org.mockito.Mockito.eq
import org.mockito.Mockito.never
import org.mockito.MockedStatic
import org.mockito.Mockito.mockStatic
import java.awt.event.MouseEvent

class RunSelectedInjectedActionTest {

    @Test
    fun testActionPerformedWithInjectedVariable() {
        // Create mocks
        val mockEvent = mock(AnActionEvent::class.java)
        val mockProject = mock(Project::class.java)
        val mockEditor = mock(Editor::class.java)
        val mockCaretModel = mock(CaretModel::class.java)
        val mockFile = mock(PsiFile::class.java)
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        val mockElement = mock(PsiElement::class.java)
        val mockMouseEvent = mock(MouseEvent::class.java)
        
        // Configure mocks
        `when`(mockEvent.project).thenReturn(mockProject)
        `when`(mockEvent.getData(CommonDataKeys.EDITOR)).thenReturn(mockEditor)
        `when`(mockEvent.getData(CommonDataKeys.PSI_FILE)).thenReturn(mockFile)
        `when`(mockEvent.inputEvent).thenReturn(mockMouseEvent)
        `when`(mockEditor.caretModel).thenReturn(mockCaretModel)
        `when`(mockCaretModel.offset).thenReturn(100)
        `when`(mockFile.findElementAt(100)).thenReturn(mockElement)
        
        // Create action with mocked dependencies
        val action = object : RunSelectedInjectedAction() {
            override fun createHelper(project: Project): InjectedFunctionActionHelper {
                return mockHelper
            }
        }
        
        // Mock static methods
        mockStatic(PinjectedDetectionUtil::class.java).use { mockedDetectionUtil ->
            mockStatic(GutterActionUtil::class.java).use { mockedGutterUtil ->
                // Configure static mocks
                mockedDetectionUtil.`when`<String?> { PinjectedDetectionUtil.getInjectedTargetName(mockElement) }
                    .thenReturn("test_injected")
                
                // Execute action
                action.actionPerformed(mockEvent)
                
                // Verify that GutterActionUtil methods were called
                mockedGutterUtil.verify { GutterActionUtil.createActions(mockProject, "test_injected") }
                mockedGutterUtil.verify { GutterActionUtil.showPopupChooser(eq(mockMouseEvent), any()) }
                
                // Verify no notification was shown
                verify(mockHelper, never()).showNotification(any(), any(), any())
            }
        }
    }

    @Test
    fun testActionPerformedWithNoInjectedVariable() {
        // Create mocks
        val mockEvent = mock(AnActionEvent::class.java)
        val mockProject = mock(Project::class.java)
        val mockEditor = mock(Editor::class.java)
        val mockCaretModel = mock(CaretModel::class.java)
        val mockFile = mock(PsiFile::class.java)
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        val mockElement = mock(PsiElement::class.java)
        
        // Configure mocks
        `when`(mockEvent.project).thenReturn(mockProject)
        `when`(mockEvent.getData(CommonDataKeys.EDITOR)).thenReturn(mockEditor)
        `when`(mockEvent.getData(CommonDataKeys.PSI_FILE)).thenReturn(mockFile)
        `when`(mockEditor.caretModel).thenReturn(mockCaretModel)
        `when`(mockCaretModel.offset).thenReturn(100)
        `when`(mockFile.findElementAt(100)).thenReturn(mockElement)
        
        // Create action with mocked dependencies
        val action = object : RunSelectedInjectedAction() {
            override fun createHelper(project: Project): InjectedFunctionActionHelper {
                return mockHelper
            }
        }
        
        // Mock static methods
        mockStatic(PinjectedDetectionUtil::class.java).use { mockedDetectionUtil ->
            // Configure static mocks to return null (no injected found)
            mockedDetectionUtil.`when`<String?> { PinjectedDetectionUtil.getInjectedTargetName(mockElement) }
                .thenReturn(null)
            
            // Execute action
            action.actionPerformed(mockEvent)
            
            // Verify notification was shown for no injected found
            verify(mockHelper).showNotification(
                eq("No Injected Found"), 
                eq("No injected function or variable found at the current cursor position"), 
                eq(NotificationType.INFORMATION)
            )
        }
    }
    
    @Test
    fun testActionPerformedWithNullElement() {
        // Create mocks
        val mockEvent = mock(AnActionEvent::class.java)
        val mockProject = mock(Project::class.java)
        val mockEditor = mock(Editor::class.java)
        val mockCaretModel = mock(CaretModel::class.java)
        val mockFile = mock(PsiFile::class.java)
        val mockHelper = mock(InjectedFunctionActionHelper::class.java)
        
        // Configure mocks
        `when`(mockEvent.project).thenReturn(mockProject)
        `when`(mockEvent.getData(CommonDataKeys.EDITOR)).thenReturn(mockEditor)
        `when`(mockEvent.getData(CommonDataKeys.PSI_FILE)).thenReturn(mockFile)
        `when`(mockEditor.caretModel).thenReturn(mockCaretModel)
        `when`(mockCaretModel.offset).thenReturn(100)
        `when`(mockFile.findElementAt(100)).thenReturn(null)
        
        // Create action with mocked dependencies
        val action = object : RunSelectedInjectedAction() {
            override fun createHelper(project: Project): InjectedFunctionActionHelper {
                return mockHelper
            }
        }
        
        // Execute action
        action.actionPerformed(mockEvent)
        
        // Verify no notification was shown (since elementAt is null, the outer if condition will handle it)
        verify(mockHelper, never()).showNotification(any(), any(), any())
    }
}
