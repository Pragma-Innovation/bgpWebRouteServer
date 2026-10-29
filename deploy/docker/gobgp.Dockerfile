FROM golang:1.23-alpine AS builder

ARG GOBGP_VERSION=v3.31.0

RUN apk add --no-cache git gcc musl-dev && \
    go install github.com/osrg/gobgp/v3/cmd/gobgpd@${GOBGP_VERSION} && \
    go install github.com/osrg/gobgp/v3/cmd/gobgp@${GOBGP_VERSION}

FROM alpine:3.20

COPY --from=builder /go/bin/gobgpd /usr/local/bin/gobgpd
COPY --from=builder /go/bin/gobgp /usr/local/bin/gobgp

EXPOSE 179 50051

ENTRYPOINT ["gobgpd"]
CMD ["-f", "/etc/gobgp/gobgp.yaml", "--api-hosts", ":50051"]
