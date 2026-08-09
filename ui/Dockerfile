# The browser talks to the backend directly, so the API base URL is baked at build time and
# must point at the host-published backend port, not the in-network service name.
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Serve the built assets with Vite preview on 5173 so the browser origin matches the backend
# CORS allow-list default; keeping one port avoids a CORS mismatch between build and runtime.
FROM node:22-slim AS runtime
WORKDIR /app
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/vite.config.ts ./
COPY --from=build /app/dist ./dist
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
