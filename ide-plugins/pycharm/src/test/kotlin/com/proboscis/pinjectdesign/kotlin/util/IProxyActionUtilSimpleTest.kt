package com.proboscis.pinjectdesign.kotlin.util

import com.google.gson.Gson
import org.junit.Test
import org.junit.Assert.*

/**
 * Simple unit test for IProxyActionUtil.
 * Tests basic functionality without complex mocking.
 */
class IProxyActionUtilSimpleTest {
    
    private val gson = Gson()
    
    @Test
    fun testInjectedFunctionDataClass() {
        val function = IProxyActionUtil.InjectedFunction(
            function_name = "test_func",
            module_path = "test.module",
            file_path = "/test/file.py",
            line_number = 42,
            parameter_name = "param",
            parameter_type = "TestType",
            docstring = "Test docstring"
        )
        
        assertEquals("test_func", function.function_name)
        assertEquals("test.module", function.module_path)
        assertEquals("/test/file.py", function.file_path)
        assertEquals(42, function.line_number)
        assertEquals("param", function.parameter_name)
        assertEquals("TestType", function.parameter_type)
        assertEquals("Test docstring", function.docstring)
    }
    
    @Test
    fun testJsonSerialization() {
        val function = IProxyActionUtil.InjectedFunction(
            function_name = "process_user",
            module_path = "app.processors",
            file_path = "/app/processors.py",
            line_number = 100,
            parameter_name = "user",
            parameter_type = "User",
            docstring = null
        )
        
        val json = gson.toJson(function)
        assertTrue("JSON should contain function name", json.contains("process_user"))
        assertTrue("JSON should contain module path", json.contains("app.processors"))
        
        val deserialized = gson.fromJson(json, IProxyActionUtil.InjectedFunction::class.java)
        assertEquals(function.function_name, deserialized.function_name)
        assertEquals(function.module_path, deserialized.module_path)
    }
    
    @Test
    fun testListSerialization() {
        val functions = listOf(
            IProxyActionUtil.InjectedFunction(
                function_name = "func1",
                module_path = "module1",
                file_path = "/file1.py",
                line_number = 10,
                parameter_name = "param1",
                parameter_type = "Type1",
                docstring = "Doc1"
            ),
            IProxyActionUtil.InjectedFunction(
                function_name = "func2",
                module_path = "module2",
                file_path = "/file2.py",
                line_number = 20,
                parameter_name = "param2",
                parameter_type = "Type2",
                docstring = null
            )
        )
        
        val json = gson.toJson(functions)
        val deserialized = gson.fromJson(
            json,
            Array<IProxyActionUtil.InjectedFunction>::class.java
        ).toList()
        
        assertEquals(2, deserialized.size)
        assertEquals("func1", deserialized[0].function_name)
        assertEquals("func2", deserialized[1].function_name)
        assertNull(deserialized[1].docstring)
    }
}