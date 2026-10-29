# Multi-stage Dockerfile for Vue 3 SPA
FROM node:22-alpine AS development

WORKDIR /app

COPY web/package*.json ./
RUN npm install

COPY web/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build stage
FROM development AS builder

RUN npm run build

# Production static web server (unprivileged Nginx)
FROM nginxinc/nginx-unprivileged:alpine AS production

COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config for SPA history mode routing
RUN echo 'server { \
    listen 8080; \
    server_name localhost; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
