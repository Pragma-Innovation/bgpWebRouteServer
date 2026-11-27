FROM docker.io/library/alpine:latest

# Install BIRD Internet Routing Daemon (BIRD 3 with native Flowspec)
RUN apk add --no-cache bird

# Create runtime directories
RUN mkdir -p /etc/bird /run/bird /var/log/bird

COPY configs/bird.conf /etc/bird.conf

EXPOSE 179

# Run BIRD in foreground with logging to stderr
CMD ["bird", "-d", "-c", "/etc/bird.conf"]
