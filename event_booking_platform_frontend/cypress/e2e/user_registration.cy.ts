describe('User Registration', () => {
  beforeEach(() => {
    // Visit the registration page before each test
    cy.visit('/register'); // Update this URL if your registration page is different
  });

  it('should allow a user to register with valid credentials', () => {
    const uniqueEmail = `testuser_${Date.now()}@example.com`;
    cy.get('input[name="username"]').type('testuser');
    cy.get('input[name="email"]').type(uniqueEmail);
    cy.get('input[name="password"]').type('password123');
    cy.get('input[name="passwordConfirmation"]').type('password123'); // Assuming this is the name of confirm password field

    cy.get('button[type="submit"]').click();

    // Assertion: Check for redirection to login page or a success message.
    // This depends on your application's flow.
    // Option 1: Check for redirection to login
    cy.url().should('include', '/login');
    // Option 2: Or check for a success message on the registration page (if not redirected)
    // cy.contains('Registration successful! Please login.').should('be.visible');

    // Optional: Attempt to log in with new credentials
    // This might require navigating to login, filling form, and asserting successful login.
    // cy.visit('/login');
    // cy.get('input[name="email"]').type(uniqueEmail); // Or username if that's used for login
    // cy.get('input[name="password"]').type('password123');
    // cy.get('button[type="submit"]').click();
    // cy.url().should('not.include', '/login'); // Should redirect away from login on success
    // cy.contains('Welcome, testuser').should('be.visible'); // Example of a post-login assertion
  });

  it('should display validation errors for empty form submission', () => {
    cy.get('button[type="submit"]').click();

    // Assert that validation messages appear for each required field
    // Adjust selectors and messages based on your actual form
    cy.get('input[name="username"]')
      .siblings('.error-message')
      .should('be.visible')
      .and('contain', 'Username is required');
    cy.get('input[name="email"]')
      .siblings('.error-message')
      .should('be.visible')
      .and('contain', 'Email is required');
    cy.get('input[name="password"]')
      .siblings('.error-message')
      .should('be.visible')
      .and('contain', 'Password is required');
    cy.get('input[name="passwordConfirmation"]')
      .siblings('.error-message')
      .should('be.visible')
      .and('contain', 'Password confirmation is required');
  });

  it('should display validation error for invalid email format', () => {
    cy.get('input[name="username"]').type('testuser');
    cy.get('input[name="email"]').type('invalid-email');
    cy.get('input[name="password"]').type('password123');
    cy.get('input[name="passwordConfirmation"]').type('password123');
    cy.get('button[type="submit"]').click();

    cy.get('input[name="email"]')
      .siblings('.error-message')
      .should('be.visible')
      .and('contain', 'Invalid email format');
  });

  it('should display validation error for mismatched passwords', () => {
    cy.get('input[name="username"]').type('testuser');
    cy.get('input[name="email"]').type(`mismatch_${Date.now()}@example.com`);
    cy.get('input[name="password"]').type('password123');
    cy.get('input[name="passwordConfirmation"]').type('password456'); // Mismatched password
    cy.get('button[type="submit"]').click();

    cy.get('input[name="passwordConfirmation"]')
      .siblings('.error-message')
      .should('be.visible')
      .and('contain', 'Passwords do not match');
  });

  // Add more tests as needed:
  // - Minimum/maximum length for username/password
  // - Username already taken (requires mocking API or specific backend state)
  // - Email already registered (requires mocking API or specific backend state)
});
