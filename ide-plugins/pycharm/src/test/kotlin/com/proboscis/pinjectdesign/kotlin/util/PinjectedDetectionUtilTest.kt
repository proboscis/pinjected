package com.proboscis.pinjectdesign.kotlin.util

import com.jetbrains.python.psi.PyDecorator
import com.jetbrains.python.psi.PyDecoratorList
import com.jetbrains.python.psi.PyFunction
import com.jetbrains.python.psi.PyTargetExpression
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.mockito.Mockito.mock
import org.mockito.Mockito.`when`

class PinjectedDetectionUtilTest {

    @Test
    fun testGetInjectedTargetNameForInjectedFunction() {
        // Create mock PyFunction
        val mockFunction = mock(PyFunction::class.java)
        val mockDecoratorList = mock(PyDecoratorList::class.java)
        val mockDecorator = mock(PyDecorator::class.java)
        
        // Configure mocks
        `when`(mockFunction.name).thenReturn("injected_function")
        `when`(mockFunction.decoratorList).thenReturn(mockDecoratorList)
        `when`(mockDecoratorList.decorators).thenReturn(arrayOf(mockDecorator))
        `when`(mockDecorator.name).thenReturn("injected")
        
        // Test
        val result = PinjectedDetectionUtil.getInjectedTargetName(mockFunction)
        
        // Verify
        assertEquals("Should return the function name for injected function", "injected_function", result)
    }

    @Test
    fun testGetInjectedTargetNameForInjectedVariable() {
        // Create mock PyTargetExpression
        val mockVariable = mock(PyTargetExpression::class.java)
        
        // Configure mock
        `when`(mockVariable.name).thenReturn("injected_var")
        
        // For this test, we'll need to mock the type inference system
        // This is a simplified test that assumes the variable is injected
        // In a real implementation, we would need to mock more complex behavior
        
        // Test
        val result = PinjectedDetectionUtil.getInjectedTargetName(mockVariable)
        
        // This test may need to be updated based on the actual implementation
        // For now, we're just verifying the basic structure
        assertEquals("Should return the variable name for injected variable", "injected_var", result)
    }

    @Test
    fun testGetInjectedTargetNameForNonInjectedElement() {
        // Create mock PyFunction without injected decorator
        val mockFunction = mock(PyFunction::class.java)
        val mockDecoratorList = mock(PyDecoratorList::class.java)
        
        // Configure mocks
        `when`(mockFunction.name).thenReturn("regular_function")
        `when`(mockFunction.decoratorList).thenReturn(mockDecoratorList)
        `when`(mockDecoratorList.decorators).thenReturn(arrayOf())
        
        // Test
        val result = PinjectedDetectionUtil.getInjectedTargetName(mockFunction)
        
        // Verify
        assertNull("Should return null for non-injected function", result)
    }
}
