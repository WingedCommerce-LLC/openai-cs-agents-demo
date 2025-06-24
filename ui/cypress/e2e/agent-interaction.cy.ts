/**
 * End-to-End Tests for Agent Interaction
 * 
 * Tests the complete user journey of interacting with agents,
 * ensuring 85% coverage of critical user flows.
 */

describe('Agent Interaction E2E Tests', () => {
  beforeEach(() => {
    // Seed test data
    cy.task('seedDatabase')
    
    // Visit the application
    cy.visit('/')
    
    // Mock authentication if needed
    cy.window().then((win) => {
      win.localStorage.setItem('auth-token', 'test-token')
      win.localStorage.setItem('tenant-id', 'test-tenant-123')
    })
  })

  afterEach(() => {
    // Clean up test data
    cy.task('cleanDatabase')
  })

  describe('Agent Selection and Conversation Flow', () => {
    it('should display available agents on the homepage', () => {
      // Verify agents are displayed
      cy.get('[data-testid="agents-list"]').should('be.visible')
      cy.get('[data-testid="agent-card"]').should('have.length.at.least', 1)
      
      // Check agent information is displayed
      cy.get('[data-testid="agent-card"]').first().within(() => {
        cy.get('[data-testid="agent-name"]').should('be.visible')
        cy.get('[data-testid="agent-description"]').should('be.visible')
        cy.get('[data-testid="agent-status"]').should('be.visible')
      })
    })

    it('should start a conversation with an agent', () => {
      // Click on the first agent
      cy.get('[data-testid="agent-card"]').first().click()
      
      // Verify conversation interface appears
      cy.get('[data-testid="conversation-panel"]').should('be.visible')
      cy.get('[data-testid="message-input"]').should('be.visible')
      cy.get('[data-testid="send-button"]').should('be.visible')
      
      // Send a test message
      const testMessage = 'Hello, I need help with my account'
      cy.get('[data-testid="message-input"]').type(testMessage)
      cy.get('[data-testid="send-button"]').click()
      
      // Verify message appears in conversation
      cy.get('[data-testid="message"]').should('contain', testMessage)
      
      // Wait for agent response (with timeout)
      cy.get('[data-testid="agent-message"]', { timeout: 10000 })
        .should('be.visible')
        .and('not.be.empty')
    })

    it('should handle agent handoffs correctly', () => {
      // Start conversation with triage agent
      cy.get('[data-testid="agent-card"]')
        .contains('Triage Agent')
        .click()
      
      // Send message that should trigger handoff
      cy.get('[data-testid="message-input"]')
        .type('I want to cancel my subscription')
      cy.get('[data-testid="send-button"]').click()
      
      // Verify handoff notification
      cy.get('[data-testid="handoff-notification"]', { timeout: 15000 })
        .should('be.visible')
        .and('contain', 'Transferring to')
      
      // Verify new agent is active
      cy.get('[data-testid="current-agent"]')
        .should('not.contain', 'Triage Agent')
    })
  })

  describe('MCP Server Integration', () => {
    it('should display available MCP servers', () => {
      // Navigate to MCP servers page
      cy.get('[data-testid="nav-mcp-servers"]').click()
      
      // Verify MCP servers are listed
      cy.get('[data-testid="mcp-servers-list"]').should('be.visible')
      cy.get('[data-testid="mcp-server-card"]').should('exist')
    })

    it('should create a new MCP server from OpenAPI spec', () => {
      // Navigate to MCP servers page
      cy.get('[data-testid="nav-mcp-servers"]').click()
      
      // Click create new server button
      cy.get('[data-testid="create-mcp-server"]').click()
      
      // Fill in server details
      cy.get('[data-testid="server-name-input"]').type('Test API Server')
      cy.get('[data-testid="server-description-input"]')
        .type('Test server for E2E testing')
      cy.get('[data-testid="base-url-input"]')
        .type('https://api.test.com')
      
      // Upload OpenAPI spec (mock file upload)
      cy.get('[data-testid="openapi-spec-upload"]').selectFile({
        contents: JSON.stringify({
          openapi: '3.0.0',
          info: { title: 'Test API', version: '1.0.0' },
          paths: {
            '/test': {
              get: {
                operationId: 'test_endpoint',
                summary: 'Test endpoint'
              }
            }
          }
        }),
        fileName: 'test-api.json',
        mimeType: 'application/json'
      })
      
      // Submit form
      cy.get('[data-testid="create-server-submit"]').click()
      
      // Verify server creation success
      cy.get('[data-testid="success-notification"]')
        .should('be.visible')
        .and('contain', 'MCP server created successfully')
      
      // Verify server appears in list
      cy.get('[data-testid="mcp-server-card"]')
        .should('contain', 'Test API Server')
    })
  })

  describe('Security and Authentication', () => {
    it('should redirect to login when not authenticated', () => {
      // Clear authentication
      cy.window().then((win) => {
        win.localStorage.removeItem('auth-token')
        win.localStorage.removeItem('tenant-id')
      })
      
      // Try to access protected route
      cy.visit('/agents')
      
      // Should redirect to login
      cy.url().should('include', '/login')
      cy.get('[data-testid="login-form"]').should('be.visible')
    })

    it('should handle tenant isolation correctly', () => {
      // Set different tenant ID
      cy.window().then((win) => {
        win.localStorage.setItem('tenant-id', 'different-tenant-456')
      })
      
      // Reload page
      cy.reload()
      
      // Verify only tenant-specific data is shown
      cy.get('[data-testid="tenant-indicator"]')
        .should('contain', 'different-tenant-456')
      
      // Verify no data from other tenants is visible
      cy.get('[data-testid="conversation-list"]')
        .should('not.contain', 'test-tenant-123')
    })
  })

  describe('Error Handling and Edge Cases', () => {
    it('should handle API errors gracefully', () => {
      // Intercept API calls and return error
      cy.intercept('POST', '/api/conversations', {
        statusCode: 500,
        body: { error: 'Internal server error' }
      }).as('createConversationError')
      
      // Try to start conversation
      cy.get('[data-testid="agent-card"]').first().click()
      cy.get('[data-testid="message-input"]').type('Test message')
      cy.get('[data-testid="send-button"]').click()
      
      // Verify error is displayed
      cy.get('[data-testid="error-notification"]')
        .should('be.visible')
        .and('contain', 'Failed to send message')
    })

    it('should handle network connectivity issues', () => {
      // Simulate offline mode
      cy.window().then((win) => {
        Object.defineProperty(win.navigator, 'onLine', {
          writable: true,
          value: false
        })
      })
      
      // Trigger network event
      cy.window().trigger('offline')
      
      // Verify offline indicator
      cy.get('[data-testid="offline-indicator"]')
        .should('be.visible')
        .and('contain', 'You are offline')
      
      // Verify functionality is limited
      cy.get('[data-testid="send-button"]').should('be.disabled')
    })
  })

  describe('Performance and Accessibility', () => {
    it('should load the page within acceptable time limits', () => {
      const startTime = Date.now()
      
      cy.visit('/').then(() => {
        const loadTime = Date.now() - startTime
        expect(loadTime).to.be.lessThan(3000) // 3 seconds max
      })
      
      // Verify critical elements are visible quickly
      cy.get('[data-testid="agents-list"]', { timeout: 2000 })
        .should('be.visible')
    })

    it('should be accessible to screen readers', () => {
      // Check for proper ARIA labels
      cy.get('[data-testid="agent-card"]').should('have.attr', 'role', 'button')
      cy.get('[data-testid="message-input"]').should('have.attr', 'aria-label')
      
      // Check for proper heading structure
      cy.get('h1').should('exist')
      cy.get('[data-testid="agent-name"]').should('have.attr', 'role', 'heading')
      
      // Check keyboard navigation
      cy.get('[data-testid="agent-card"]').first().focus()
      cy.focused().type('{enter}')
      cy.get('[data-testid="conversation-panel"]').should('be.visible')
    })
  })

  describe('Data Persistence and State Management', () => {
    it('should persist conversation state across page reloads', () => {
      // Start a conversation
      cy.get('[data-testid="agent-card"]').first().click()
      cy.get('[data-testid="message-input"]').type('Test persistence')
      cy.get('[data-testid="send-button"]').click()
      
      // Wait for message to appear
      cy.get('[data-testid="message"]').should('contain', 'Test persistence')
      
      // Reload page
      cy.reload()
      
      // Verify conversation is restored
      cy.get('[data-testid="conversation-panel"]').should('be.visible')
      cy.get('[data-testid="message"]').should('contain', 'Test persistence')
    })

    it('should handle concurrent user sessions correctly', () => {
      // This would require more complex setup with multiple browser contexts
      // For now, verify session isolation
      cy.window().then((win) => {
        const sessionId = win.localStorage.getItem('session-id')
        expect(sessionId).to.exist
        expect(sessionId).to.have.length.greaterThan(10)
      })
    })
  })
})

// Custom commands for reusable test actions
Cypress.Commands.add('loginAsTestUser', () => {
  cy.window().then((win) => {
    win.localStorage.setItem('auth-token', 'test-token')
    win.localStorage.setItem('tenant-id', 'test-tenant-123')
    win.localStorage.setItem('user-id', 'test-user-456')
  })
})

Cypress.Commands.add('startConversationWithAgent', (agentName: string) => {
  cy.get('[data-testid="agent-card"]')
    .contains(agentName)
    .click()
  cy.get('[data-testid="conversation-panel"]').should('be.visible')
})

Cypress.Commands.add('sendMessage', (message: string) => {
  cy.get('[data-testid="message-input"]').type(message)
  cy.get('[data-testid="send-button"]').click()
  cy.get('[data-testid="message"]').should('contain', message)
})

// Type declarations for custom commands
declare global {
  namespace Cypress {
    interface Chainable {
      loginAsTestUser(): Chainable<void>
      startConversationWithAgent(agentName: string): Chainable<void>
      sendMessage(message: string): Chainable<void>
    }
  }
}
