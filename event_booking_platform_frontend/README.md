# Event Booking Platform Frontend

This is the frontend for the Event Booking Platform, built with Next.js.

## Getting Started

First, install the dependencies:

```bash
npm install
# or
# npm ci (recommended for CI environments or to ensure exact dependency versions)
```

Then, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You will also need the backend service running. Please refer to the main project README for instructions on running the entire application using Docker Compose.

## Environment Variables

Create a `.env.local` file in this directory by copying from `.env.local.example`. Populate it with the necessary environment variables, such as:

- `NEXT_PUBLIC_API_BASE_URL`: The base URL for the backend API.
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`: Your Stripe publishable key for client-side Stripe.js integration.

## Dependency Management

It's important to keep dependencies up-to-date and secure.

### Checking for Outdated Dependencies

To check for packages that have newer versions available, run:

```bash
npm outdated
```

This will show you a list of dependencies that are outdated. Review these and decide on updates.

### Updating Dependencies

To update dependencies to their latest versions based on the ranges specified in your `package.json`:

```bash
npm update
```

After updating, test the application thoroughly to ensure no breaking changes were introduced. Once confirmed, commit the updated `package.json` and `package-lock.json` files.

It's recommended to perform dependency updates periodically (e.g., once per sprint or month).

### Checking for Vulnerabilities

To check for known security vulnerabilities in your dependencies:

```bash
npm audit
```

This command will show a report of vulnerabilities and their severity.

To attempt to automatically fix compatible vulnerabilities:

```bash
npm audit fix
```

For some vulnerabilities, `npm audit fix --force` might be suggested, but use this with caution as it can introduce breaking changes. It's often better to manually update the affected packages or look for alternative solutions if a direct fix isn't available.

Regularly run `npm audit` and address reported vulnerabilities, especially high and critical ones, as part of your development workflow and before deployments. The CI pipeline also includes a step to check for high-severity vulnerabilities (`npm audit --audit-level=high`).

## Linting and Testing

- **Linting:** `npm run lint` or `npm run lint:ci`
- **Unit/Integration Tests:** `npm test`
- **E2E Tests (Cypress):** Refer to Cypress scripts in `package.json` (e.g., `npm run cypress:open`).

## Building for Production

```bash
npm run build
```

This will create an optimized production build in the `.next` folder.

## Learn More (Next.js)

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.
