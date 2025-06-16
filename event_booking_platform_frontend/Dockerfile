# syntax=docker/dockerfile:1

# ---- Builder Stage ----
FROM node:20-slim AS builder
# Using Node 20-slim as a more recent LTS version

WORKDIR /app

# Copy package.json and lock file
COPY package*.json ./

# Install dependencies
# Use npm ci for cleaner, more deterministic installs based on package-lock.json
RUN npm ci

# Copy the rest of the application code
COPY . .

# Build the Next.js application
RUN npm run build

# ---- Production Stage ----
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV production
# Disable Next.js telemetry during runtime
ENV NEXT_TELEMETRY_DISABLED 1

# Create a non-root user for security best practices
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built assets from the builder stage
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public # Copy public folder if it exists
# If you have a standalone server.js, copy it as well
# COPY --from=builder --chown=nextjs:nodejs /app/server.js ./server.js

# Change ownership of the app directory to the new user
# This is not strictly necessary if USER is set before CMD, but good practice for /app contents.
# RUN chown -R nextjs:nodejs /app

# Use the non-root user
USER nextjs

EXPOSE 3000

# Command to start the Next.js application
CMD ["npm", "start"]
