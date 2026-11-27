# Multi-stage Dockerfile for Vue 3 SPA
FROM docker.io/library/node:22-alpine AS development

WORKDIR /app

COPY web/package*.json ./
RUN npm install

COPY web/ ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Build stage
FROM development AS builder

ARG VITE_DEMO_MODE=false
ENV VITE_DEMO_MODE=${VITE_DEMO_MODE}

RUN npm run build

# Production static web server (unprivileged Nginx)
FROM docker.io/nginxinc/nginx-unprivileged:alpine AS production

ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    BACKEND_UPSTREAM=http://backend:8000

USER root
RUN mkdir -p /usr/share/nginx/django_static /etc/nginx/templates && \
    chown -R 101:101 /usr/share/nginx/django_static /etc/nginx/templates /etc/nginx/conf.d
USER 101

COPY --from=builder /app/dist /usr/share/nginx/html

# Template rendered at container boot with container DNS resolver & dynamic upstream resolution
RUN printf '%s\n' \
  'server {' \
  '    listen 8080;' \
  '    server_name _;' \
  '    client_max_body_size 20M;' \
  '    resolver ${NGINX_LOCAL_RESOLVERS} valid=10s ipv6=off;' \
  '' \
  '    location / {' \
  '        root /usr/share/nginx/html;' \
  '        index index.html index.htm;' \
  '        try_files $uri $uri/ /index.html;' \
  '    }' \
  '' \
  '    location /api/ {' \
  '        set $upstream ${BACKEND_UPSTREAM};' \
  '        proxy_pass $upstream;' \
  '        proxy_set_header Host $http_host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
  '        proxy_set_header X-Forwarded-Proto $scheme;' \
  '    }' \
  '' \
  '    location /admin/ {' \
  '        set $upstream ${BACKEND_UPSTREAM};' \
  '        proxy_pass $upstream;' \
  '        proxy_set_header Host $http_host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' \
  '        proxy_set_header X-Forwarded-Proto $scheme;' \
  '    }' \
  '' \
  '    location /static/ {' \
  '        alias /usr/share/nginx/django_static/;' \
  '        expires 7d;' \
  '        access_log off;' \
  '    }' \
  '}' > /etc/nginx/templates/default.conf.template

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
