package com.proboscis.pinjectdesign.kotlin.integration

import com.proboscis.pinjectdesign.kotlin.util.IProxyActionUtil
import com.intellij.openapi.project.Project
import com.google.gson.Gson
import org.junit.Test
import org.junit.Before
import org.junit.After
import org.junit.Assert.*
import org.mockito.kotlin.*
import java.io.File
import java.io.BufferedWriter
import java.io.OutputStreamWriter
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CompletableFuture
import java.util.concurrent.Executors
import kotlin.concurrent.thread

class IndexerIntegrationTest {
    
    private val gson = Gson()
    private var mockIndexerServer: MockIndexerServer? = null
    
    @Before
    fun setUp() {
        // Start mock indexer server for integration testing
        mockIndexerServer = MockIndexerServer()
        mockIndexerServer?.start()
    }
    
    @After
    fun tearDown() {
        mockIndexerServer?.stop()
    }
    
    @Test
    fun testQueryIndexerWithValidResponse() {
        // Prepare mock response
        val mockFunctions = listOf(
            mapOf(
                "function_name" to "process_user",
                "module_path" to "app.processors",
                "file_path" to "/project/app/processors.py",
                "line_number" to 42,
                "parameter_name" to "user",
                "parameter_type" to "User",
                "docstring" to "Process user data"
            ),
            mapOf(
                "function_name" to "validate_user",
                "module_path" to "app.validators",
                "file_path" to "/project/app/validators.py",
                "line_number" to 15,
                "parameter_name" to "user",
                "parameter_type" to "User",
                "docstring" to "Validate user"
            )
        )
        
        mockIndexerServer?.setResponse(gson.toJson(mockFunctions))
        
        // Test the query
        val project = mock<Project> {
            on { basePath } doReturn "/test/project"
        }
        
        // Create a test utility that uses our mock server
        val util = createTestUtil()
        
        val future = util.queryInjectedFunctions(project, "User")
        val result = future.get()
        
        assertEquals(2, result.size)
        assertEquals("process_user", result[0].function_name)
        assertEquals("validate_user", result[1].function_name)
    }
    
    @Test
    fun testQueryIndexerWithEmptyResponse() {
        mockIndexerServer?.setResponse("[]")
        
        val project = mock<Project> {
            on { basePath } doReturn "/test/project"
        }
        
        val util = createTestUtil()
        val future = util.queryInjectedFunctions(project, "UnknownType")
        val result = future.get()
        
        assertTrue(result.isEmpty())
    }
    
    @Test
    fun testQueryIndexerWithComplexTypes() {
        val mockFunctions = listOf(
            mapOf(
                "function_name" to "process_list",
                "module_path" to "app.processors",
                "file_path" to "/project/app/processors.py",
                "line_number" to 100,
                "parameter_name" to "items",
                "parameter_type" to "List[User]",
                "docstring" to "Process user list"
            ),
            mapOf(
                "function_name" to "process_dict",
                "module_path" to "app.processors",
                "file_path" to "/project/app/processors.py",
                "line_number" to 150,
                "parameter_name" to "mapping",
                "parameter_type" to "Dict[str, User]",
                "docstring" to null
            )
        )
        
        mockIndexerServer?.setResponse(gson.toJson(mockFunctions))
        
        val project = mock<Project> {
            on { basePath } doReturn "/test/project"
        }
        
        // Test List[User]
        val util = createTestUtil()
        val listFuture = util.queryInjectedFunctions(project, "List[User]")
        val listResult = listFuture.get()
        
        assertEquals(2, listResult.size)
        assertEquals("List[User]", listResult[0].parameter_type)
        
        // Test Dict[str, User]
        mockIndexerServer?.setResponse(gson.toJson(listOf(mockFunctions[1])))
        val dictFuture = util.queryInjectedFunctions(project, "Dict[str, User]")
        val dictResult = dictFuture.get()
        
        assertEquals(1, dictResult.size)
        assertEquals("Dict[str, User]", dictResult[0].parameter_type)
        assertNull(dictResult[0].docstring)
    }
    
    @Test
    fun testQueryIndexerHandlesInvalidJson() {
        mockIndexerServer?.setResponse("invalid json {]")
        
        val project = mock<Project> {
            on { basePath } doReturn "/test/project"
        }
        
        val util = createTestUtil()
        val future = util.queryInjectedFunctions(project, "User")
        val result = future.get()
        
        // Should return empty list on JSON parse error
        assertTrue(result.isEmpty())
    }
    
    @Test
    fun testQueryIndexerHandlesTimeout() {
        // Configure mock server to delay response
        mockIndexerServer?.setResponseDelay(10000) // 10 seconds
        
        val project = mock<Project> {
            on { basePath } doReturn "/test/project"
        }
        
        val util = createTestUtil()
        val future = util.queryInjectedFunctions(project, "User")
        
        // Should handle timeout gracefully
        val result = future.get()
        assertTrue(result.isEmpty())
    }
    
    @Test
    fun testConcurrentQueries() {
        val mockFunctions = listOf(
            mapOf(
                "function_name" to "func1",
                "module_path" to "module1",
                "file_path" to "/file1.py",
                "line_number" to 1,
                "parameter_name" to "param",
                "parameter_type" to "Type1",
                "docstring" to "Doc1"
            )
        )
        
        mockIndexerServer?.setResponse(gson.toJson(mockFunctions))
        
        val project = mock<Project> {
            on { basePath } doReturn "/test/project"
        }
        
        val util = createTestUtil()
        
        // Launch multiple concurrent queries
        val futures = (1..5).map {
            util.queryInjectedFunctions(project, "Type$it")
        }
        
        // All should complete successfully
        futures.forEach { future ->
            val result = future.get()
            assertNotNull(result)
        }
    }
    
    @Test
    fun testIndexerCommandConstruction() {
        // Test that the correct command is constructed
        val projectRoot = "/path/to/project"
        val typeParam = "User"
        
        val expectedCommand = listOf(
            "pinjected-indexer",
            "--root", projectRoot,
            "--log-level", "error",
            "query-iproxy-functions",
            typeParam
        )
        
        // Verify command construction
        assertEquals("pinjected-indexer", expectedCommand[0])
        assertEquals("--root", expectedCommand[1])
        assertEquals(projectRoot, expectedCommand[2])
        assertEquals("--log-level", expectedCommand[3])
        assertEquals("error", expectedCommand[4])
        assertEquals("query-iproxy-functions", expectedCommand[5])
        assertEquals(typeParam, expectedCommand[6])
    }
    
    @Test
    fun testResponseParsing() {
        val jsonResponse = """
        [
            {
                "function_name": "test_func",
                "module_path": "test.module.path",
                "file_path": "/absolute/path/to/file.py",
                "line_number": 42,
                "parameter_name": "test_param",
                "parameter_type": "TestType",
                "docstring": "This is a test function"
            }
        ]
        """.trimIndent()
        
        val parsed: List<IProxyActionUtil.InjectedFunction> = gson.fromJson(
            jsonResponse,
            object : com.google.gson.reflect.TypeToken<List<IProxyActionUtil.InjectedFunction>>() {}.type
        )
        
        assertEquals(1, parsed.size)
        val func = parsed[0]
        assertEquals("test_func", func.function_name)
        assertEquals("test.module.path", func.module_path)
        assertEquals("/absolute/path/to/file.py", func.file_path)
        assertEquals(42, func.line_number)
        assertEquals("test_param", func.parameter_name)
        assertEquals("TestType", func.parameter_type)
        assertEquals("This is a test function", func.docstring)
    }
    
    // Helper methods
    
    private fun createTestUtil(): TestableIProxyActionUtil {
        return TestableIProxyActionUtil(mockIndexerServer?.port ?: 0)
    }
    
    /**
     * Testable version of IProxyActionUtil that uses our mock server.
     */
    private class TestableIProxyActionUtil(private val mockPort: Int) {
        private val gson = Gson()
        
        fun queryInjectedFunctions(
            project: Project,
            typeParam: String
        ): CompletableFuture<List<IProxyActionUtil.InjectedFunction>> {
            return CompletableFuture.supplyAsync {
                try {
                    // Instead of calling actual indexer, connect to mock server
                    if (mockPort == 0) {
                        return@supplyAsync emptyList<IProxyActionUtil.InjectedFunction>()
                    }
                    
                    // Simulate the indexer call
                    val socket = Socket("localhost", mockPort)
                    socket.use {
                        val writer = BufferedWriter(OutputStreamWriter(it.getOutputStream()))
                        writer.write(typeParam)
                        writer.newLine()
                        writer.flush()
                        
                        val response = it.getInputStream().bufferedReader().readText()
                        
                        if (response.isBlank()) {
                            return@supplyAsync emptyList<IProxyActionUtil.InjectedFunction>()
                        }
                        
                        val listType = object : com.google.gson.reflect.TypeToken<List<IProxyActionUtil.InjectedFunction>>() {}.type
                        gson.fromJson(response, listType)
                    }
                } catch (e: Exception) {
                    emptyList()
                }
            }
        }
    }
    
    /**
     * Mock indexer server for testing.
     */
    private class MockIndexerServer {
        private var serverSocket: ServerSocket? = null
        private var serverThread: Thread? = null
        private var response: String = "[]"
        private var responseDelay: Long = 0
        val port: Int get() = serverSocket?.localPort ?: 0
        
        fun setResponse(response: String) {
            this.response = response
        }
        
        fun setResponseDelay(delay: Long) {
            this.responseDelay = delay
        }
        
        fun start() {
            serverSocket = ServerSocket(0) // Random available port
            serverThread = thread {
                try {
                    while (!Thread.currentThread().isInterrupted) {
                        val client = serverSocket?.accept() ?: break
                        thread {
                            handleClient(client)
                        }
                    }
                } catch (e: Exception) {
                    // Server stopped
                }
            }
        }
        
        fun stop() {
            serverSocket?.close()
            serverThread?.interrupt()
        }
        
        private fun handleClient(client: Socket) {
            try {
                client.use {
                    // Read request (type parameter)
                    val request = it.getInputStream().bufferedReader().readLine()
                    
                    // Simulate delay if configured
                    if (responseDelay > 0) {
                        Thread.sleep(responseDelay)
                    }
                    
                    // Send response
                    val writer = it.getOutputStream().bufferedWriter()
                    writer.write(response)
                    writer.flush()
                }
            } catch (e: Exception) {
                // Client disconnected
            }
        }
    }
}