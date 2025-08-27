package com.proboscis.pinjectdesign.kotlin.lineMarkers

import org.junit.Before
import org.junit.Test
import org.junit.Assert.*

/**
 * Simple unit test for IProxyGutterIconProvider.
 * Tests the provider exists and can be instantiated.
 */
class IProxyGutterIconProviderSimpleTest {
    
    private lateinit var provider: IProxyGutterIconProvider
    
    @Before
    fun setUp() {
        provider = IProxyGutterIconProvider()
    }
    
    @Test
    fun testProviderExists() {
        assertNotNull("Provider should be created", provider)
    }
    
    @Test
    fun testProviderIsNotNull() {
        // Since getLineMarkerInfo requires non-null PsiElement,
        // we just test that the provider itself is properly created
        assertTrue("Provider should be an instance of IProxyGutterIconProvider", 
                   provider is IProxyGutterIconProvider)
    }
}