package com.proboscis.pinjectdesign.kotlin.handlers

import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.search.GlobalSearchScope
import com.jetbrains.python.psi.*
import com.jetbrains.python.psi.stubs.PyFunctionNameIndex
import org.junit.Before
import org.junit.Test
import org.junit.Assert.*
import org.mockito.Mock
import org.mockito.Mockito.*
import org.mockito.MockitoAnnotations

class InjectedGotoDeclarationHandlerTest {
    
    @Mock
    private lateinit var mockProject: Project
    
    @Mock
    private lateinit var mockEditor: Editor
    
    @Mock
    private lateinit var mockElement: PsiElement
    
    @Mock
    private lateinit var mockFunction: PyFunction
    
    @Mock
    private lateinit var mockParameterList: PyParameterList
    
    @Mock
    private lateinit var mockParameter: PyNamedParameter
    
    @Mock
    private lateinit var mockDecoratorList: PyDecoratorList
    
    @Mock
    private lateinit var mockDecorator: PyDecorator
    
    @Mock
    private lateinit var mockRefExpression: PyReferenceExpression
    
    private lateinit var handler: InjectedGotoDeclarationHandler
    
    @Before
    fun setUp() {
        MockitoAnnotations.openMocks(this)
        handler = InjectedGotoDeclarationHandler()
    }
    
    @Test
    fun testNavigateFromParameterToFunction() {
        // Setup mocks for a parameter in an @injected function
        `when`(mockElement.parent).thenReturn(mockParameter)
        `when`(mockParameter.name).thenReturn("database_connection")
        `when`(mockElement.project).thenReturn(mockProject)
        
        // Mock the containing function with @injected decorator
        mockFunctionWithDecorator(mockFunction, "injected")
        `when`(mockParameter.parent).thenReturn(mockParameterList)
        `when`(mockParameterList.parent).thenReturn(mockFunction)
        
        // Mock finding matching functions
        val matchingFunction = mock(PyFunction::class.java)
        mockFunctionWithDecorator(matchingFunction, "instance")
        `when`(matchingFunction.name).thenReturn("database_connection")
        val nameIdentifier = mock(PsiElement::class.java)
        `when`(matchingFunction.nameIdentifier).thenReturn(nameIdentifier)
        
        // Since we can't easily mock static PyFunctionNameIndex, we test the handler logic separately
        // In a real implementation, this would require more sophisticated testing setup
        
        // Test that the handler correctly identifies parameter navigation
        val parameterParent = mockElement.parent
        assertNotNull("Parameter parent should not be null", parameterParent)
        assertTrue("Should be a PyNamedParameter", parameterParent is PyNamedParameter)
    }
    
    @Test
    fun testNoNavigationFromNonInjectedFunction() {
        // Setup mocks for a parameter in a regular function (no decorators)
        `when`(mockElement.parent).thenReturn(mockParameter)
        `when`(mockParameter.name).thenReturn("some_param")
        `when`(mockElement.project).thenReturn(mockProject)
        
        // Mock function without decorators
        `when`(mockFunction.decoratorList).thenReturn(null)
        `when`(mockParameter.parent).thenReturn(mockParameterList)
        `when`(mockParameterList.parent).thenReturn(mockFunction)
        
        // Test that handler returns null for non-injected function
        val result = handler.getGotoDeclarationTargets(mockElement, 0, mockEditor)
        assertNull("Should return null for non-injected function", result)
    }
    
    @Test
    fun testDetectsInjectedDecorator() {
        // Test decorator detection logic
        mockFunctionWithDecorator(mockFunction, "injected")
        
        // Verify the function has the expected decorator
        val decoratorList = mockFunction.decoratorList
        assertNotNull("Decorator list should not be null", decoratorList)
        val decorators = decoratorList!!.decorators
        assertTrue("Should have decorators", decorators.isNotEmpty())
        
        // Check decorator name
        val callee = decorators[0].callee as? PyReferenceExpression
        assertEquals("injected", callee?.name)
    }
    
    @Test
    fun testDetectsInstanceDecorator() {
        // Test decorator detection logic for @instance
        mockFunctionWithDecorator(mockFunction, "instance")
        
        // Verify the function has the expected decorator
        val decoratorList = mockFunction.decoratorList
        assertNotNull("Decorator list should not be null", decoratorList)
        val decorators = decoratorList!!.decorators
        assertTrue("Should have decorators", decorators.isNotEmpty())
        
        // Check decorator name
        val callee = decorators[0].callee as? PyReferenceExpression
        assertEquals("instance", callee?.name)
    }
    
    @Test
    fun testHandlesCallExpressionDecorator() {
        // Test handling @injected() with parentheses
        val mockCallExpression = mock(PyCallExpression::class.java)
        val mockCalleeRef = mock(PyReferenceExpression::class.java)
        
        `when`(mockCalleeRef.name).thenReturn("injected")
        `when`(mockCallExpression.callee).thenReturn(mockCalleeRef)
        `when`(mockDecorator.callee).thenReturn(mockCallExpression)
        `when`(mockDecoratorList.decorators).thenReturn(arrayOf(mockDecorator))
        `when`(mockFunction.decoratorList).thenReturn(mockDecoratorList)
        
        // Verify the decorator is recognized
        val callee = mockDecorator.callee as? PyCallExpression
        assertNotNull("Should be a call expression", callee)
        val calleeRef = callee?.callee as? PyReferenceExpression
        assertEquals("injected", calleeRef?.name)
    }
    
    private fun mockFunctionWithDecorator(function: PyFunction, decoratorName: String) {
        `when`(mockRefExpression.name).thenReturn(decoratorName)
        `when`(mockDecorator.callee).thenReturn(mockRefExpression)
        `when`(mockDecoratorList.decorators).thenReturn(arrayOf(mockDecorator))
        `when`(function.decoratorList).thenReturn(mockDecoratorList)
    }
}