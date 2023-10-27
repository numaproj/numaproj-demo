FROM golang:1.19-alpine AS build
WORKDIR /app
COPY . .
RUN go build -o traffic-analyzer

FROM alpine:latest
COPY --from=build /app/traffic-analyzer /app/traffic-analyzer
CMD ["/app/traffic-analyzer"]